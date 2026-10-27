"""Run diagnose.py's two options on the 96 Reddit "advice that worked" threads and grade the answers.

    python eval_resolved.py                    # Haiku; resumes: answers and grades already on disk are skipped
    python eval_resolved.py --model claude-opus-5-5

For each thread (data/reddit/resolved/threads.csv), the model sees only the post: the question's photos, its title and
OP's text (the `question` column). Option `llm` sends that alone, option `llm+classifier` adds the DINOv2 classifier's
output for each photo (same prompt as diagnose.py). A grader model then compares each answer, without knowing which
option produced it, with the thread's confirmed problem, the advice that worked and OP's outcome.

Writes results/llm/resolved-<model>/{classifier.json, answers/<thread>__<option>.json, grades/...json} and
reports/llm-resolved-<model>.md.
"""

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import nb
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from diagnose import CLASSIFIER_NOTE, MODEL, ask, build_prompt

OPTIONS = ["llm", "llm+classifier"]
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0, "yes": 1.0, "no": 0.0}
BORDERLINE = {"1gj7tyl", "1kbiakb", "1bytyxl", "1ao6rfb", "1u3kg0t"}  # listed in data/reddit/resolved/README.md

GRADER_PROMPT = """You grade an answer to a Reddit post asking what is wrong with a houseplant. The thread is resolved:
the poster followed some advice and said it worked. Compare the answer with that reference.

Reference, from the thread:
- Confirmed problem: {problem}
- Advice given by commenters (the poster followed some or all of it): {answer}
- What the poster said afterwards: {outcome}

Answer to grade:
<answer>
{response}
</answer>

Grade:
- diagnosis: "correct" if the answer's main diagnosis is the confirmed problem; "partial" if the answer names it but
  only as one possibility among several or not as the main cause, or gets only part of it; "wrong" otherwise.
- advice: "yes" if following the answer's main advice would most likely have produced the same fix; "partial" if the
  fix is in the answer but buried among other suggestions or incomplete; "no" otherwise.
- harmful: true if the answer recommends something likely to make this plant worse given the confirmed problem.
- reason: one short sentence."""

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "diagnosis": {"type": "string", "enum": ["correct", "partial", "wrong"]},
        "advice": {"type": "string", "enum": ["yes", "partial", "no"]},
        "harmful": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["diagnosis", "advice", "harmful", "reason"],
    "additionalProperties": False,
}


def split_question(row, image_cols):
    """Question photos in reading order, title, and OP's text (the photo placeholders removed)."""
    photos = [row[c] for c in re.findall(r"(?<!\{)\{(Image_\d\d)\}", row.question)]
    title, _, body = row.question.format(**{c: "" for c in image_cols}).partition("\n\n")
    return photos, title.strip(), body.strip()


@nb.core
def grade(client, model, row, image_cols, response):
    prompt = GRADER_PROMPT.format(problem=row.problem, answer=row.answer, response=response,
                                  outcome=row.outcome.format(**{c: "[photo]" for c in image_cols}))
    r = client.messages.create(model=model, max_tokens=4000, output_config={"format": {"type": "json_schema", "schema": GRADE_SCHEMA}},
                               messages=[{"role": "user", "content": prompt}])
    return json.loads(next(b.text for b in r.content if b.type == "text")), r.usage


def bootstrap(x, n=10000, seed=0):
    """Mean and 95% bootstrap interval over threads."""
    x = np.asarray(x, float)
    m = np.random.default_rng(seed).choice(x, size=(n, len(x))).mean(1)
    return x.mean(), np.quantile(m, 0.025), np.quantile(m, 0.975)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL, help="model that answers the posts")
    p.add_argument("--grader", default=MODEL, help="model that grades the answers")
    p.add_argument("--head", default="results/all-224px/head.npz")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    load_dotenv(Path(__file__).parent / ".env")
    client = anthropic.Anthropic(max_retries=8)

    df = pd.read_csv("data/reddit/resolved/threads.csv", dtype=str, keep_default_na=False)
    image_cols = [c for c in df.columns if c.startswith("Image_")]
    out = Path(f"results/llm/resolved-{args.model.removeprefix('claude-')}")
    (out / "answers").mkdir(parents=True, exist_ok=True)
    (out / "grades").mkdir(exist_ok=True)

    # 1. Classifier output for every question photo, computed once.
    cls_path = out / "classifier.json"
    if not cls_path.exists():
        from predict import probabilities
        photos = sorted({p for _, r in df.iterrows() for p in split_question(r, image_cols)[0]})
        labels, prob = probabilities(args.head, photos)
        json.dump({ph: dict(zip(labels.tolist(), row.round(4).tolist())) for ph, row in zip(photos, prob)}, open(cls_path, "w"), indent=1)
    cls = json.load(open(cls_path))

    def classifier_text(photos):
        return "\n".join(f"Photo {i}: " + ", ".join(f"{l} {p:.0%}" for l, p in sorted(cls[ph].items(), key=lambda x: -x[1]))
                         for i, ph in enumerate(photos, 1))

    # 2. Answers, then 3. grades; each saved as soon as it arrives.
    def answer_and_grade(job):
        row, option = job
        name = f"{row.thread_id}__{option}.json"
        a_path, g_path = out / "answers" / name, out / "grades" / name
        if not a_path.exists():
            photos, title, body = split_question(row, image_cols)
            prompt = build_prompt(title, body, classifier_text(photos) if option == "llm+classifier" else None)
            text, r = ask(client, photos, prompt, args.model)
            json.dump({"thread_id": row.thread_id, "option": option, "model": r.model, "photos": photos, "prompt": prompt,
                       "answer": text, "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}, open(a_path, "w"), indent=1)
        if not g_path.exists():
            g, u = grade(client, args.grader, row, image_cols, json.load(open(a_path))["answer"])
            json.dump({**g, "grader": args.grader, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens}, open(g_path, "w"), indent=1)
        return name

    jobs = [(r, o) for _, r in df.iterrows() for o in OPTIONS]
    with ThreadPoolExecutor(args.workers) as pool:
        for k, name in enumerate(pool.map(answer_and_grade, jobs), 1):
            if k % 20 == 0 or k == len(jobs):
                print(f"{k}/{len(jobs)} {name}", flush=True)

    # 4. Scores per option, with 95% intervals over threads, and the paired difference.
    rows = []
    for _, r in df.iterrows():
        for o in OPTIONS:
            a = json.load(open(out / "answers" / f"{r.thread_id}__{o}.json"))
            g = json.load(open(out / "grades" / f"{r.thread_id}__{o}.json"))
            rows.append(dict(thread_id=r.thread_id, option=o, diagnosis=g["diagnosis"], advice=g["advice"], harmful=g["harmful"],
                             diag_score=SCORE[g["diagnosis"]], advice_score=SCORE[g["advice"]], reason=g["reason"],
                             answer_in=a["input_tokens"], answer_out=a["output_tokens"], grade_in=g["input_tokens"], grade_out=g["output_tokens"]))
    res = pd.DataFrame(rows)
    res.to_csv(out / "scores.csv", index=False)
    print_report(res, df, args, out)


def fmt(m, lo, hi):
    return f"{m:.2f} [{lo:.2f}, {hi:.2f}]"


def print_report(res, df, args, out):
    wide = {k: res.pivot(index="thread_id", columns="option", values=k) for k in ["diag_score", "advice_score", "harmful"]}
    table, finals = [], {}
    for o in OPTIONS:
        d = res[res.option == o]
        finals[o] = dict(diag_score=d.diag_score.mean(), advice_score=d.advice_score.mean(), harmful_rate=d.harmful.mean(),
                         diag_correct=(d.diagnosis == "correct").mean(), n_threads=len(d))
        table.append({"option": o,
                      "diagnosis score": fmt(*bootstrap(d.diag_score)),
                      "diagnosis correct / partial / wrong": "/".join(str((d.diagnosis == v).sum()) for v in ["correct", "partial", "wrong"]),
                      "advice score": fmt(*bootstrap(d.advice_score)),
                      "advice yes / partial / no": "/".join(str((d.advice == v).sum()) for v in ["yes", "partial", "no"]),
                      "harmful answers": int(d.harmful.sum())})
    diff = {k: wide[k]["llm+classifier"] - wide[k]["llm"] for k in ["diag_score", "advice_score"]}
    keep = ~wide["diag_score"].index.isin(BORDERLINE)
    paired = pd.DataFrame([{"score": k, "all 96 threads": fmt(*bootstrap(v)),
                            f"without the {len(BORDERLINE)} borderline threads": fmt(*bootstrap(v[keep])),
                            "threads better / same / worse with classifier": f"{(v > 0).sum()} / {(v == 0).sum()} / {(v < 0).sum()}"}
                           for k, v in diff.items()])
    p_in, p_out = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20)}[next(k for k in ["haiku", "sonnet", "opus"] if k in args.model)]
    g_in, g_out = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20)}[next(k for k in ["haiku", "sonnet", "opus"] if k in args.grader)]
    cost = (res.answer_in.sum() * p_in + res.answer_out.sum() * p_out + res.grade_in.sum() * g_in + res.grade_out.sum() * g_out) / 1e6

    report = f"""# Claude on 96 resolved Reddit threads, with and without the classifier ({args.model})

Data: `data/reddit/resolved/threads.csv`, 96 threads where the poster said the advice worked. The model under test sees only
the post (its photos, title and the poster's text, the `question` column) and is asked "What is wrong with my plant?"
(`diagnose.py`). Option `llm+classifier` also gets the DINOv2 classifier's probabilities for each photo
(`{args.head}`), with its 5 classes and a warning that it is unreliable on phone photos.

Grading: `{args.grader}` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of this run: ${cost:.2f}.

## Scores (higher is better)

{pd.DataFrame(table).to_markdown(index=False)}

## Classifier minus no classifier, paired by thread

{paired.to_markdown(index=False)}

Per-thread grades and reasons: `{out}/scores.csv`. Answers: `{out}/answers/`.
"""
    path = f"reports/llm-resolved-{args.model.removeprefix('claude-')}.md"
    open(path, "w").write(report)
    print(report)

    for o in OPTIONS:  # one tracker experiment per option; the option without classifier is the baseline
        run = nb.start(
            subproject="llm-diagnosis",
            title=f"{args.model.removeprefix('claude-').replace('-', ' ', 1).replace('-', '.').title()}, {'post + classifier output' if o != 'llm' else 'post only'}",
            formula=r"answer $= \mathrm{LLM}(\text{photos}, \text{post}" + (r", p(y \mid x_j)" if o != "llm" else "") + r")$, graded by \cfg{grader} against the thread's fix",
            algo="llm-diagnosis",
            config=dict(model=args.model, grader=args.grader, option=o, classifier=args.head, n_threads=len(df)),
            question="Does adding the DINOv2 classifier's output to the prompt help Claude diagnose real Reddit plant posts?",
            baseline=o == "llm" and "haiku" in args.model,
        )
        run.finish(**finals[o])


if __name__ == "__main__":
    main()
