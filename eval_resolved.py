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
import difflib
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

from diagnose import BLOCKED_DOMAINS, MODEL, ask, build_prompt, system_prompt

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
    r = client.messages.create(model=model, max_tokens=8000, output_config={"format": {"type": "json_schema", "schema": GRADE_SCHEMA}},
                               messages=[{"role": "user", "content": prompt}])
    return json.loads(next(b.text for b in r.content if b.type == "text")), r.usage


def possible_leaks(searches, title):
    """Search results that may be the thread itself: a blocked (Reddit or mirror) domain, or a page title close to the post's."""
    leaks = []
    for s in searches:
        for x in s.get("results", []):
            host = re.sub(r"^https?://([^/]+).*", r"\1", x.get("url", "")).lower()
            same = difflib.SequenceMatcher(None, x.get("title", "").lower(), title.lower()).ratio()
            if any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS) or (len(title) > 15 and same > 0.6):
                leaks.append({**x, "title_similarity": round(same, 2)})
    return leaks


def bootstrap(x, n=10000, seed=0):
    """Mean and 95% bootstrap interval over threads."""
    x = np.asarray(x, float)
    m = np.random.default_rng(seed).choice(x, size=(n, len(x))).mean(1)
    return x.mean(), np.quantile(m, 0.025), np.quantile(m, 0.975)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL, help="model that answers the posts")
    p.add_argument("--grader", default=MODEL, help="model that grades the answers")
    p.add_argument("--head", default="results/all-224px/head.npz")
    p.add_argument("--prompt", default="plain", help="system prompt of the answering model: plain, guided, guided-v2 or "
                   "guided-v2+<element>+... (diagnose.ELEMENTS)")
    p.add_argument("--effort", default="medium", help="effort of the answering model")
    p.add_argument("--max_threads", type=int, help="only the first N threads of the split (in its random order)")
    p.add_argument("--samples", type=int, default=1, help="answers per thread and option; scores are averaged per thread")
    p.add_argument("--sub", help="tracker subproject (default: llm-prompts for test, llm-diagnosis otherwise)")
    p.add_argument("--threads", choices=["all", "dev", "test"], default="all",
                   help="dev: 32 threads for writing prompts; test: the other 64, held out (seed 0)")
    p.add_argument("--search", nargs="?", const="always", default=False,
                   help="the answering model may search the web (Reddit and its mirrors blocked); 'unsure': only if unsure")
    p.add_argument("--options", default=",".join(OPTIONS))
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--track", action="store_true", help="record one experiment per option on the lab site")
    args = p.parse_args(argv)
    load_dotenv(Path(__file__).parent / ".env")
    client = anthropic.Anthropic(max_retries=20)

    df = pd.read_csv("data/reddit/resolved/threads.csv", dtype=str, keep_default_na=False)
    image_cols = [c for c in df.columns if c.startswith("Image_")]
    dev = set(np.random.default_rng(0).permutation(sorted(df.thread_id))[:32])
    if args.threads != "all":
        df = df[df.thread_id.isin(dev) == (args.threads == "dev")].reset_index(drop=True)
    if args.max_threads:
        order = {t: i for i, t in enumerate(np.random.default_rng(0).permutation(sorted(df.thread_id)))}
        df = df.iloc[sorted(range(len(df)), key=lambda i: order[df.thread_id[i]])[:args.max_threads]].reset_index(drop=True)
    options = args.options.split(",")
    out = Path(f"results/llm/resolved-{args.model.removeprefix('claude-')}" + ("" if args.prompt == "plain" else f"-{args.prompt}")
               + ("" if not args.search else "-search" if args.search == "always" else f"-search-{args.search}")
               + ("" if args.effort == "medium" else f"-{args.effort}"))
    (out / "answers").mkdir(parents=True, exist_ok=True)
    gdir = "grades" if args.grader == MODEL else f"grades-{args.grader.removeprefix('claude-')}"
    (out / gdir).mkdir(exist_ok=True)
    system = system_prompt(args.prompt)

    # 1. Classifier output for every question photo, computed once.
    cls_path = Path("results/llm/classifier-resolved.json")
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
    def file_name(thread, option, k):  # sample 0 keeps the original name, so earlier single-answer runs are reused
        return f"{thread}__{option}.json" if k == 0 else f"{thread}__{option}__s{k}.json"

    def answer_and_grade(job):
        row, option, k = job
        name = file_name(row.thread_id, option, k)
        a_path, g_path = out / "answers" / name, out / gdir / name
        if not a_path.exists():
            photos, title, body = split_question(row, image_cols)
            prompt = build_prompt(title, body, classifier_text(photos) if option == "llm+classifier" else None)
            text, r, usage, searches = ask(client, photos, prompt, args.model, system, args.search, args.effort)
            if not text.strip():  # e.g. thinking used the whole output budget; not saved, so a rerun retries it
                print(f"empty answer for {name} (stop reason {r.stop_reason}); not saved", flush=True)
                return name
            json.dump({"thread_id": row.thread_id, "option": option, "model": r.model, "photos": photos, "prompt": prompt,
                       "answer": text, "system_prompt": args.prompt, **usage, "searches": searches,
                       "possible_leaks": possible_leaks(searches, title)}, open(a_path, "w"), indent=1)
        if not g_path.exists():
            g, u = grade(client, args.grader, row, image_cols, json.load(open(a_path))["answer"])
            json.dump({**g, "grader": args.grader, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens}, open(g_path, "w"), indent=1)
        return name

    jobs = [(r, o, k) for _, r in df.iterrows() for o in options for k in range(args.samples)]
    with ThreadPoolExecutor(args.workers) as pool:
        for k, name in enumerate(pool.map(answer_and_grade, jobs), 1):
            if k % 20 == 0 or k == len(jobs):
                print(f"{k}/{len(jobs)} {name}", flush=True)

    # 4. Scores per option, with 95% intervals over threads, and the paired difference.
    rows = []
    for _, r in df.iterrows():
        for o in options:
          for k in range(args.samples):
            a = json.load(open(out / "answers" / file_name(r.thread_id, o, k)))
            g = json.load(open(out / gdir / file_name(r.thread_id, o, k)))
            rows.append(dict(thread_id=r.thread_id, option=o, sample=k, diagnosis=g["diagnosis"], advice=g["advice"], harmful=g["harmful"],
                             diag_score=SCORE[g["diagnosis"]], advice_score=SCORE[g["advice"]], reason=g["reason"],
                             searches=a.get("web_search_requests", 0), possible_leaks=len(a.get("possible_leaks", [])),
                             answer_in=a["input_tokens"], answer_out=a["output_tokens"], grade_in=g["input_tokens"], grade_out=g["output_tokens"]))
    res = pd.DataFrame(rows)
    tag = args.threads + ("" if args.grader == MODEL else f"-{gdir.removeprefix('grades-')}")
    res.to_csv(out / f"scores-{tag}.csv", index=False)
    print_report(res, df, args, out, options, tag)


def fmt(m, lo, hi):
    return f"{m:.2f} [{lo:.2f}, {hi:.2f}]"


def print_report(res, df, args, out, options, tag):
    n = len(df)
    table, finals = [], {}
    per_thread = res.groupby(["thread_id", "option"], as_index=False)[["diag_score", "advice_score", "harmful"]].mean()
    for o in options:
        d, dt = res[res.option == o], per_thread[per_thread.option == o]
        finals[o] = dict(diag_score=d.diag_score.mean(), advice_score=d.advice_score.mean(), harmful_rate=d.harmful.mean(),
                         diag_correct=(d.diagnosis == "correct").mean(), n_threads=len(dt), samples=args.samples)
        table.append({"option": o,
                      "diagnosis score": fmt(*bootstrap(dt.diag_score)),
                      "diagnosis correct / partial / wrong": "/".join(str((d.diagnosis == v).sum()) for v in ["correct", "partial", "wrong"]),
                      "advice score": fmt(*bootstrap(dt.advice_score)),
                      "advice yes / partial / no": "/".join(str((d.advice == v).sum()) for v in ["yes", "partial", "no"]),
                      "harmful answers": int(d.harmful.sum())})
    paired = ""
    if set(OPTIONS) <= set(options):
        wide = {k: per_thread.pivot(index="thread_id", columns="option", values=k) for k in ["diag_score", "advice_score"]}
        diff = {k: wide[k]["llm+classifier"] - wide[k]["llm"] for k in wide}
        keep = ~wide["diag_score"].index.isin(BORDERLINE)
        paired = "## Classifier minus no classifier, paired by thread\n\n" + pd.DataFrame([
            {"score": k, f"all {n} threads": fmt(*bootstrap(v)), "without the borderline threads": fmt(*bootstrap(v[keep])),
             "threads better / same / worse with classifier": f"{(v > 0).sum()} / {(v == 0).sum()} / {(v < 0).sum()}"}
            for k, v in diff.items()]).to_markdown(index=False) + "\n"
    price = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20)}  # USD per 1M tokens
    p_in, p_out = price[next(k for k in price if k in args.model)]
    g_in, g_out = price[next(k for k in price if k in args.grader)]
    cost = (res.answer_in.sum() * p_in + res.answer_out.sum() * p_out + res.grade_in.sum() * g_in + res.grade_out.sum() * g_out) / 1e6
    cost += res.searches.sum() * 10 / 1000  # web search: $10 per 1,000 searches
    search_note = "" if not args.search else (
        f"\nWeb search: the answering model could run up to 3 searches per answer (`web_search` tool; Reddit, its image hosts "
        f"and Reddit mirrors/archives blocked). It ran {res.searches.mean():.1f} per answer on average. Answers whose results include "
        f"a page that may be the thread itself (blocked domain, or a title close to the post's): "
        f"{(res.possible_leaks > 0).sum()} of {len(res)} (listed under `possible_leaks` in each answer file).\n")
    subset = {"all": "all 96 threads", "dev": "the 32 development threads", "test": "the 64 held-out test threads"}[args.threads]

    report = f"""# Claude on resolved Reddit threads ({args.model}, {args.prompt} prompt{", web search" if args.search else ""}, {subset})

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here {subset} (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `{args.prompt}`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`{args.head}`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `{args.grader}` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. With several answers per thread
({args.samples}), scores are averaged per thread first. Brackets: 95% bootstrap interval over threads. Cost of the calls behind these numbers: ${cost:.2f}.
{search_note}
## Scores (higher is better)

{pd.DataFrame(table).to_markdown(index=False)}

{paired}
Per-thread grades and reasons: `{out}/scores-{tag}.csv`. Answers: `{out}/answers/`.
"""
    name = args.model.removeprefix("claude-") + ("" if args.prompt == "plain" else f"-{args.prompt}") + ("" if not args.search else "-search" if args.search == "always" else f"-search-{args.search}") + ("" if args.threads == "all" else f"-{args.threads}") \
        + ("" if args.grader == MODEL else f"-graded-{args.grader.removeprefix('claude-')}")
    open(f"reports/llm-resolved-{name}.md", "w").write(report)
    print(report)
    if not args.track:
        return
    words = {"kb": "plant-care notes", "priors": "common causes ranked", "question": "answer the asked question",
             "differential": "weigh 3 causes first", "format": "short fixed format",
             "lead": "fix stated first", "short": "at most 150 words", "drop5": "without other-causes item",
             "drop6": "without may-be-normal item", "drop7": "without weigh-poster-details item",
             "drop2": "without watering item", "drop4": "without pests item"}
    base, *elements = args.prompt.split("+")
    prompt_words = base + "".join(f" + {words[e]}" for e in elements)
    for o in options:  # one tracker experiment per option
        run = nb.start(
            subproject=args.sub or ("llm-prompts" if args.threads == "test" else "llm-diagnosis"),
            title=((f"{args.model.removeprefix('claude-').split('-')[0].title()} {args.effort} effort, " if args.model != MODEL or args.effort != "medium" else "")
                   + f"{prompt_words}" + (", no search" if not args.search else ", web search" if args.search == "always" else
                      ", web research (up to 5 searches)" if args.search == "research" else ", web search if unsure")
                   + (", held-out test threads" if args.threads == "test" else ", all 96 threads" if args.threads == "all" else "")) if args.sub else
                  f"{args.model.removeprefix('claude-').replace('-', ' ', 1).replace('-', '.').title()}, {args.prompt} prompt, "
                  f"{'post + classifier output' if o != 'llm' else 'post only'}" + (", web search" if args.search else ""),
            formula=r"answer $= \mathrm{LLM}(\text{photos}, \text{post}" + (r", p(y \mid x_j)" if o != "llm" else "")
                    + r")$ with system prompt \cfg{prompt}, graded by \cfg{grader} against the thread's fix",
            algo="llm-diagnosis",
            config=dict(model=args.model, grader=args.grader, prompt=args.prompt, option=o, classifier=args.head, search=args.search,
                        threads=args.threads, n_threads=n, samples=args.samples, effort=args.effort),
            question="Which additions to the guided-v2 system prompt (plant-care notes, answer format, ...), with or without web "
                     "search, make Haiku's answers match the fix that worked more often on the 32 development threads?" if args.sub else
                     "Does a guided system prompt help Claude diagnose real Reddit plant posts, and does the classifier help on top of it?"
                     if args.threads == "test" else
                     "Does adding the DINOv2 classifier's output to the prompt help Claude diagnose real Reddit plant posts?",
            baseline=(args.prompt == "guided-v2" and not args.search) if args.sub else
                     (args.threads == "test" and o == "llm" and args.prompt == "plain"),
        )
        run.finish(**finals[o])


if __name__ == "__main__":
    main()
