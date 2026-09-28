"""Step 1: zero-shot classify test-set images with Gemini and score against the labels.

python classify.py                      # the 100 Indoor images
python classify.py --source all --n 200 # the whole test set
Results go to data/preds/<model>.csv; rerunning skips images already done.
"""

import argparse
import time
from pathlib import Path

import pandas as pd

import llm

p = argparse.ArgumentParser()
p.add_argument("--source", default="indoor", help="indoor / wilted / plantseg / all")
p.add_argument("--n", type=int, default=100)
p.add_argument("--model", default=llm.MODEL)
p.add_argument("--sleep", type=float, default=4.0, help="seconds between calls (free-tier per-minute limit)")
args = p.parse_args()

df = pd.read_csv("data/testset.csv")
if args.source != "all":
    df = df[df.source == args.source]
df = df.head(args.n)

out = Path("data/preds") / f"{args.model}.csv"
out.parent.mkdir(parents=True, exist_ok=True)
done = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["image", "pred"])
seen = set(done.image)

rows = done.to_dict("records")
todo = df[~df.image.isin(seen)]
print(f"{args.model}: {len(todo)} to classify, {len(df) - len(todo)} already done")
for i, r in enumerate(todo.itertuples(), 1):
    try:
        pred = llm.classify(r.image, model=args.model)
    except Exception as e:  # keep going; failed rows are retried on the next run
        print(f"  failed on {r.image}: {e}")
        continue
    rows.append(dict(image=r.image, pred=pred))
    pd.DataFrame(rows).to_csv(out, index=False)  # save after every call
    print(f"  [{i}/{len(todo)}] {r.label:>16} -> {pred}")
    time.sleep(args.sleep)

res = df.merge(pd.DataFrame(rows, columns=["image", "pred"]), on="image")
print(f"\nAccuracy: {(res.label == res.pred).mean():.1%} on {len(res)} images")
print(pd.crosstab(res.label, res.pred, rownames=["true"], colnames=["pred"]))
