"""Score a run from run_system.py; write results/<run>.json and a row of results/summary.csv.

    python evaluate.py runs/<run> [--task native] [--baseline runs/<other>] [--judge] [--check-urls] [--price-in X --price-out Y]

--task broad (default) scores the 5 labels; native scores the 16 plant + condition classes.
Prices are USD per 1M tokens, used when the system reports tokens but not cost.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from dotenv import load_dotenv

from harness import metrics
from harness.data import LABELS, native_labels, test_set


def load(run_dir, task):
    rows = [json.loads(line) for line in (run_dir / "outputs.jsonl").read_text().splitlines()]
    df = pd.DataFrame([dict(image=r["image"], case_id=r["case_id"], stages=r["stages"], remedies=r.get("remedies"),
                            pred=(r.get("diagnosis") or {}).get("label")) for r in rows])
    df = test_set().merge(df, on="image")
    assert len(df) == len(test_set()), f"{run_dir}: expected {len(test_set())} cases, found {len(df)}"
    df["truth"] = df.label if task == "broad" else df.orig_label
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--task", choices=["broad", "native"], default="broad")
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--check-urls", action="store_true")
    ap.add_argument("--price-in", type=float)
    ap.add_argument("--price-out", type=float)
    args = ap.parse_args()
    load_dotenv()

    df = load(args.run_dir, args.task)
    labels = LABELS if args.task == "broad" else native_labels()
    r = dict(run=args.run_dir.name, task=args.task)
    if df.pred.notna().any():
        r["classification"] = metrics.classification(df.truth.tolist(), df.pred.tolist(), labels)
    if args.baseline:
        base = load(args.baseline, args.task).set_index("image").loc[df.image]
        r["vs_baseline"] = dict(run=args.baseline.name, **metrics.mcnemar((df.pred == df.truth).to_numpy(), (base.pred == base.truth).to_numpy()))
    if (rem := metrics.remedies(df, args.check_urls)) is not None:
        r["remedies"] = rem
        if args.judge:
            from harness import judge
            r["judge"] = metrics.judged(judge.judge(df[df.remedies.notna()].to_dict("records"), args.run_dir))
    r["business"] = metrics.business(df, args.price_in, args.price_out)

    out = Path("results")
    out.mkdir(exist_ok=True)
    (out / f"{r['run']}.json").write_text(json.dumps(r, indent=2) + "\n")
    row = dict(run=r["run"], task=r["task"], accuracy=dig(r, "classification", "accuracy"),
               balanced_accuracy=dig(r, "classification", "balanced_accuracy"), any_harm_flag=dig(r, "remedies", "any_harm_flag"),
               safe_and_useful=dig(r, "judge", "safe_and_useful"), severe_harm=dig(r, "judge", "severe_harm"),
               error_rate=dig(r, "business", "error_rate"), latency_p95_ms=dig(r, "business", "latency_ms", "p95"),
               cost_usd_per_1000=dig(r, "business", "cost_usd_per_1000"), baseline_mcnemar_p=dig(r, "vs_baseline", "p"))
    summary = out / "summary.csv"
    rows = [x for x in (pd.read_csv(summary).to_dict("records") if summary.exists() else []) if (x["run"], x["task"]) != (row["run"], row["task"])]
    pd.DataFrame(rows + [row]).to_csv(summary, index=False)
    for k, v in row.items():
        print(f"{k:20} {v}")
    print(f"full report: {out / (r['run'] + '.json')}")


def dig(d, *path):
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
    return d


if __name__ == "__main__":
    main()
