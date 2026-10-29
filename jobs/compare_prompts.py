"""Spend so far and paired comparison of prompt variants on the dev threads (Sonnet grades). On dev, guided-v2's first answers
(the ones it was chosen on) are left out.

    python jobs/compare_prompts.py [threads=dev] [reference=guided-v2]
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

threads = sys.argv[1] if len(sys.argv) > 1 else "dev"
ref = sys.argv[2] if len(sys.argv) > 2 else "guided-v2"
PRICE = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20)}

spend = 0.0
for d in glob.glob("results/llm/resolved-haiku-5-5-guided-v2*"):
    for f in glob.glob(f"{d}/answers/*.json"):
        a = json.load(open(f))
        if "web_search_requests" in a or "__s" in f or "+" in d or "search" in d:
            spend += (a["input_tokens"] * 0.10 + a["output_tokens"] * 0.50) / 1e6 + a.get("web_search_requests", 0) * 0.01
    for f in glob.glob(f"{d}/grades-*/*.json"):
        g = json.load(open(f))
        pi, po = PRICE[next(k for k in PRICE if k in g["grader"])]
        spend += (g["input_tokens"] * pi + g["output_tokens"] * po) / 1e6
print(f"API spend on prompt design so far (excluding earlier single-sample guided-v2 answers): ${spend:.2f}\n")


def per_thread(d):
    f = Path(d) / f"scores-{threads}-sonnet-5-5.csv"
    if not f.exists():
        return None
    s = pd.read_csv(f, dtype={"thread_id": str})
    if d.endswith("resolved-haiku-5-5-guided-v2") and threads == "dev":
        s = s[s["sample"] > 0]  # sample 0 = the answers guided-v2 was chosen on (winner's curse); keep fresh ones only
    return s.groupby("thread_id")[["diag_score", "advice_score", "harmful"]].mean(), s


def boot(x, n=10000):
    m = np.random.default_rng(0).choice(x, size=(n, len(x))).mean(1)
    return f"{x.mean():+.3f} [{np.quantile(m, .025):+.3f}, {np.quantile(m, .975):+.3f}]"


rows = []
for d in ["results/llm/resolved-haiku-5-5"] + sorted(glob.glob("results/llm/resolved-haiku-5-5-guided-v2*")):
    name = d.split("resolved-haiku-5-5-")[1] if "-5-5-" in d else "plain"
    r = per_thread(d)
    if r is None:
        continue
    t, s = r
    search = name.endswith("-search")
    base = per_thread(f"results/llm/resolved-haiku-5-5-{ref}" + ("-search" if search else ""))
    row = {"variant": name, "answers": len(s), "diagnosis": f"{t.diag_score.mean():.3f}", "advice": f"{t.advice_score.mean():.3f}",
           "harmful": f"{t.harmful.mean():.3f}", "searches/answer": f"{s.searches.mean():.1f}" if "searches" in s else "",
           "leaks": int((s.possible_leaks > 0).sum()) if "possible_leaks" in s else ""}
    if base is not None and name != ref + ("-search" if search else ""):
        b = base[0].loc[t.index]
        row["advice vs " + ref] = boot((t.advice_score - b.advice_score).to_numpy())
        row["diagnosis vs " + ref] = boot((t.diag_score - b.diag_score).to_numpy())
    rows.append(row)
print(pd.DataFrame(rows).to_markdown(index=False))
