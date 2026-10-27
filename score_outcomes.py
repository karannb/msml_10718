"""Summarize the hand-judged recommendation baselines on the Reddit cases.

    python score_outcomes.py

Reads data/reddit_baselines.csv (one row per case, system and condition) and writes
results/reddit_baselines_summary.csv. Only cases with a usable reference are scored.
  coverage  chosen (main answer is the reference) | mentioned (among several causes) | missed | false_alarm
            Reference coverage = chosen or mentioned.
  solved    yes when the advice is appropriate, has no harm flag and has at most 4 short actions
            (each under 15 minutes and at most $15); blank where the advice can't be reviewed.
  harm      yes when the advice or reassurance could worsen the condition.
"""

import math
from pathlib import Path

import pandas as pd

from harness.metrics import wilson

ORDER = {"false_alarm": 0, "missed": 1, "mentioned": 2, "chosen": 3}


def rate(k, n):
    return dict(k=k, n=n, rate=round(k / n, 3) if n else None, ci=wilson(k, n))


def sign_test(better, worse):
    # Exact two-sided sign test on cases whose coverage changed.
    n, k = better + worse, min(better, worse)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0


def fmt(r):
    return f"{r['k']}/{r['n']} = {r['rate']:.0%} [{r['ci'][0]:.0%}, {r['ci'][1]:.0%}]" if r["n"] else "–"


def main():
    df = pd.read_csv("data/reddit_baselines.csv", dtype={"case_id": str})
    scored = df[df.coverage.notna()]
    rows = []
    for (system, condition), g in scored.groupby(["system", "condition"], sort=False):
        covered = g.coverage.isin(["chosen", "mentioned"])
        clean = g.source_post_retrieved.astype(str) != "True"
        reviewed = g[g.solved.notna()]
        rows.append(dict(
            system=system, condition=condition, n=len(g),
            coverage=rate(int(covered.sum()), len(g)), chosen=rate(int((g.coverage == "chosen").sum()), len(g)),
            false_alarm=int((g.coverage == "false_alarm").sum()),
            coverage_not_retrieved=rate(int(covered[clean].sum()), int(clean.sum())),
            solved=rate(int((reviewed.solved == "yes").sum()), len(reviewed)),
            harm=rate(int((reviewed.harm == "yes").sum()), len(reviewed)),
        ))

    flat = []
    for r in rows:
        row = {k: v for k, v in r.items() if not isinstance(v, dict)}
        for name, v in r.items():
            if isinstance(v, dict):
                row |= {f"{name}_k": v["k"], f"{name}_n": v["n"], f"{name}_rate": v["rate"],
                        f"{name}_ci_lo": v["ci"][0], f"{name}_ci_hi": v["ci"][1]}
        flat.append(row)
    Path("results").mkdir(exist_ok=True)
    pd.DataFrame(flat).to_csv("results/reddit_baselines_summary.csv", index=False)

    print(f"{scored.case_id.nunique()} cases with a usable reference; "
          f"{df.case_id.nunique() - scored.case_id.nunique()} unconfirmed cases recorded but not scored\n")
    for r in rows:
        print(f"{r['system']} · {r['condition']}")
        print(f"  reference coverage  {fmt(r['coverage'])}   (main answer {r['chosen']['k']}, false alarms {r['false_alarm']})")
        if r["coverage_not_retrieved"]["n"] < r["n"]:
            print(f"  coverage, source post not retrieved  {fmt(r['coverage_not_retrieved'])}")
        if r["solved"]["n"]:
            print(f"  solved              {fmt(r['solved'])}")
            print(f"  potential harm      {fmt(r['harm'])}")

    print("\nAdding the poster's details (same system, same cases, coverage scale):")
    for system, g in scored.groupby("system", sort=False):
        wide = g.pivot(index="case_id", columns="condition", values="coverage").dropna()
        if wide.shape[1] != 2:
            continue
        base, plus = g.condition.unique()
        diff = wide[plus].map(ORDER) - wide[base].map(ORDER)
        better, worse = int((diff > 0).sum()), int((diff < 0).sum())
        print(f"  {system}: {better} better, {worse} worse, {int((diff == 0).sum())} unchanged of {len(diff)}"
              f" (sign test p = {sign_test(better, worse):.2f})")
    print("\nwrote results/reddit_baselines_summary.csv")


if __name__ == "__main__":
    main()
