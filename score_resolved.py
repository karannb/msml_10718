"""Score eval_resolved.py's answers with the eval_methodology.md metrics.

    python score_resolved.py                                  # Haiku's answers, graded by Opus
    python score_resolved.py --model claude-opus-5-5 --grader claude-opus-5-5
    python score_resolved.py --baseline claude-sonnet-5-5:llm   # also compare each option with an already scored run

One grader call per answer with prompts/resolved_grader.txt (diagnosis, false alarm, advice, harm, actions), cached in
results/llm/resolved-<model>/grades-<grader>/. Writes reports/eval-resolved-<model>.md and
results/llm/resolved-<model>/eval-<grader>.csv.
  Reference coverage: diagnosis correct or partial.
  Solved: advice "yes", not harmful, and at most 4 short actions (each under 15 min/day and at most $15).
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv

from harness import rules
from harness.metrics import mcnemar, wilson

OPTIONS = ["llm", "llm+classifier"]
PRICE = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20)}  # USD per 1M tokens, as in eval_resolved.py
ACTION = {"type": "object", "additionalProperties": False, "required": ["action", "minutes", "per_day", "cost_usd", "unclear"],
          "properties": {"action": {"type": "string"}, "minutes": {"type": "number"}, "per_day": {"type": "integer"},
                         "cost_usd": {"type": "number"}, "unclear": {"type": "boolean"}}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["diagnosis", "false_alarm", "advice", "harmful", "actions", "reason"],
          "properties": {"diagnosis": {"type": "string", "enum": ["correct", "partial", "wrong"]}, "false_alarm": {"type": "boolean"},
                         "advice": {"type": "string", "enum": ["yes", "partial", "no"]}, "harmful": {"type": "boolean"},
                         "actions": {"type": "array", "items": ACTION}, "reason": {"type": "string"}}}


def grade(client, model, prompt, path, schema=SCHEMA):
    if path.exists():
        return json.loads(path.read_text())
    r = client.messages.create(model=model, max_tokens=8000, output_config={"format": {"type": "json_schema", "schema": schema}},
                               messages=[{"role": "user", "content": prompt}])
    out = json.loads(next(b.text for b in r.content if b.type == "text")) | {
        "grader": model, "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
    path.write_text(json.dumps(out, indent=1) + "\n")
    return out


def rate(x):
    k, n = int(sum(x)), len(x)
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.0%} [{lo:.0%}, {hi:.0%}]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="claude-haiku-5-5", help="the model whose answers are scored")
    ap.add_argument("--grader", default="claude-opus-5-5")
    ap.add_argument("--baseline", help="MODEL:OPTION already scored by the same grader, e.g. claude-sonnet-5-5:llm")
    args = ap.parse_args()
    load_dotenv()
    short = lambda m: m.removeprefix("claude-")
    price = lambda m: PRICE[next(k for k in PRICE if k in m)]

    run = Path(f"results/llm/resolved-{short(args.model)}")
    cache = run / f"grades-{short(args.grader)}"
    cache.mkdir(exist_ok=True)
    template = Path("prompts/resolved_grader.txt").read_text()
    threads = pd.read_csv("data/reddit/resolved/threads.csv", dtype=str, keep_default_na=False)
    image_cols = [c for c in threads.columns if c.startswith("Image_")]
    client = anthropic.Anthropic(max_retries=8)

    def score(job):
        row, option = job
        name = f"{row.thread_id}__{option}.json"
        a = json.loads((run / "answers" / name).read_text())
        g = grade(client, args.grader, template.format(problem=row.problem, answer=row.answer, response=a["answer"],
                  outcome=row.outcome.format(**{c: "[photo]" for c in image_cols})), cache / name)
        return dict(thread_id=row.thread_id, option=option, problem=row.problem, text=a["answer"],
                    **{k: g[k] for k in SCHEMA["required"]}, answer_in=a["input_tokens"], answer_out=a["output_tokens"],
                    grade_in=g["input_tokens"], grade_out=g["output_tokens"])

    with ThreadPoolExecutor(8) as ex:
        df = pd.DataFrame(ex.map(score, [(row, o) for row in threads.itertuples() for o in OPTIONS]))

    healthy = df.problem.str.contains(r"^healthy|\(healthy plant", case=False)
    is_short = lambda a: a["minutes"] * a["per_day"] < 15 and a["cost_usd"] <= 15 and not a["unclear"]
    df["n_actions"] = df.actions.map(len)
    df["within_capacity"] = df.actions.map(lambda acts: len(acts) <= 4 and all(map(is_short, acts)))
    df["covered"] = df.diagnosis.isin(["correct", "partial"])
    df["solved"] = (df.advice == "yes") & ~df.harmful & df.within_capacity
    df["harm_flag"] = [any(rules.flags(t, "healthy" if h else "sick").values()) for t, h in zip(df.text, healthy)]
    (p_in, p_out), (g_in, g_out) = price(args.model), price(args.grader)

    rows = []
    for o, d in df.groupby("option", sort=False):
        rows.append({"option": o, "reference coverage": rate(d.covered), "diagnosis correct": rate(d.diagnosis == "correct"),
                     "solved": rate(d.solved), "solved without the capacity rule": rate((d.advice == "yes") & ~d.harmful),
                     "potential harm (grader)": rate(d.harmful), "harm flag (rules)": rate(d.harm_flag),
                     "false alarm (healthy threads)": rate(d.false_alarm[healthy[d.index]]),
                     "within capacity": rate(d.within_capacity), "actions per answer": f"{d.n_actions.mean():.1f}",
                     "USD per 1,000 answers": f"{(d.answer_in * p_in + d.answer_out * p_out).mean() / 1e3:.2f}"})
    wide = {k: df.pivot(index="thread_id", columns="option", values=k) for k in ["covered", "solved", "harmful"]}
    paired = [{"this vs baseline": "llm+classifier vs llm", "metric": k, **mcnemar(w["llm+classifier"].to_numpy(bool), w["llm"].to_numpy(bool))}
              for k, w in wide.items()]
    if args.baseline:
        m, o = args.baseline.rsplit(":", 1)
        b = pd.read_csv(f"results/llm/resolved-{short(m)}/eval-{short(args.grader)}.csv", dtype={"thread_id": str})
        b = b[b.option == o].set_index("thread_id")
        paired += [{"this vs baseline": f"{opt} vs {args.baseline}", "metric": k,
                    **mcnemar(w[opt].to_numpy(bool), b.loc[w.index, k].to_numpy(bool))} for opt in OPTIONS for k, w in wide.items()]

    agreement = ""
    if (run / "grades").exists():
        other = pd.DataFrame([json.loads((run / "grades" / f"{t}__{o}.json").read_text()) for t, o in zip(df.thread_id, df.option)])
        agreement = "Agreement with the original Haiku grades (`grades/`): " + ", ".join(
            f"{k} {(df[k].to_numpy() == other[k].to_numpy()).mean():.0%}" for k in ["diagnosis", "advice", "harmful"]) + ".\n"
    cost = (df.grade_in.sum() * g_in + df.grade_out.sum() * g_out) / 1e6

    df.drop(columns=["actions", "text"]).to_csv(run / f"eval-{short(args.grader)}.csv", index=False)
    report = f"""# eval_methodology.md metrics: {args.model} on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `{args.grader}` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost ${cost:.2f}). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
{df[healthy].thread_id.nunique()} threads are healthy plants. Brackets: 95% Wilson interval.

{pd.DataFrame(rows).set_index("option").T.to_markdown()}

Paired by thread (McNemar; for harmful, "correct" = harmful):

{pd.DataFrame(paired).to_markdown(index=False)}

{agreement}
Per-answer results: `{run}/eval-{short(args.grader)}.csv`; grades with listed actions: `{cache}/`.
"""
    Path(f"reports/eval-resolved-{short(args.model)}.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
