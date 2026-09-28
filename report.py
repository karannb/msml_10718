"""Step 2: write reports/<model>.md from data/preds/<model>.csv.

python report.py                      # default model from .env / llm.py
python report.py --model gemini-3.7-flash
"""

import argparse
from pathlib import Path

import pandas as pd

import llm

p = argparse.ArgumentParser()
p.add_argument("--model", default=llm.MODEL)
args = p.parse_args()

d = pd.read_csv("data/testset.csv").merge(pd.read_csv(f"data/preds/{args.model}.csv"), on="image")
d["ok"] = d.label == d.pred
sources = ", ".join(sorted(d.source.unique()))


def md(df):
    return df.to_markdown()


per_label = d.groupby("label").ok.agg(n="size", correct="sum")
per_label["accuracy"] = (per_label.correct / per_label.n).map("{:.0%}".format)
per_class = d.groupby(["orig_label", "label"]).agg(
    n=("ok", "size"), correct=("ok", "sum"),
    predictions=("pred", lambda s: ", ".join(f"{k} {v}" for k, v in s.value_counts().items())))
confusion = pd.crosstab(d.label, d.pred, rownames=["true"], colnames=["pred"])

# Classes whose 16 -> 5 mapping is a judgment call in build_testset.py.
JUDGMENT = ["Snake_Plant_Leaf_Withering", "Spider_Plant_Leaf_Tip_Necrosis", "Money_Plant_Manganese_Toxicity"]
clear = d[~d.orig_label.isin(JUDGMENT)]

# Guessers that never look at the image, for comparison.
n, K = len(d), len(llm.LABELS)
share = d.label.value_counts(normalize=True).reindex(llm.LABELS, fill_value=0)
acc = d.ok.mean()
balanced = d.groupby("label").ok.mean().mean()  # mean of per-label accuracies
baselines = pd.DataFrame(
    [
        ["Uniform random: each label with prob. 1/K", "1/K", 1 / K, 1 / K],
        ["Stratified random: label k with prob. p_k", "sum_k p_k^2", (share ** 2).sum(), 1 / K],
        [f"Majority class: always `{share.idxmax()}`", "max_k p_k", share.max(), 1 / K],
        [f"`{args.model}`", "", acc, balanced],
    ],
    columns=["Predictor", "Expected accuracy", "Accuracy", "Balanced accuracy"],
)
for c in ["Accuracy", "Balanced accuracy"]:
    baselines[c] = baselines[c].map("{:.0%}".format)

report = f"""# Zero-shot LLM baseline: `{args.model}`

**Accuracy: {d.ok.mean():.0%} ({d.ok.sum()}/{len(d)})** on the {sources} test images of `data/testset.csv`.
Without the 3 classes whose label mapping is a judgment call ({", ".join(f"`{c}`" for c in JUDGMENT)}):
**{clear.ok.mean():.0%} ({clear.ok.sum()}/{len(clear)})**.

## Setup

- Model: `{args.model}` (Gemini API free tier), temperature 0, one image per call, no plant name given.
- Output constrained to one of the 5 labels (`text/x.enum` response schema), so every answer is a valid label.
- Prompt (`llm.py`):

```
{llm.PROMPT}
```

- Reproduce: `python classify.py --model {args.model}` then `python report.py --model {args.model}`.

## Comparison with random baselines

K = {K} labels; p_k = share of test images with true label k ({", ".join(f"{l} {v:.2f}" for l, v in share.items())}).
Balanced accuracy = mean over labels of the per-label accuracy; any guesser that ignores the image scores 1/K on it.

{baselines.to_markdown(index=False)}

With n = {n} images the accuracy is uncertain by about ±{(acc * (1 - acc) / n) ** 0.5:.0%} (one standard deviation, sqrt(a(1-a)/n)).

## Accuracy per label

{md(per_label)}

## Confusion matrix

{md(confusion)}

## Per original class

{per_class.reset_index().to_markdown(index=False)}
"""
out = Path("reports") / f"{args.model}.md"
out.parent.mkdir(exist_ok=True)
notes = out.read_text().split("\n## Observations", 1) if out.exists() else []
if len(notes) == 2:
    report = report.rstrip() + "\n\n## Observations" + notes[1]
out.write_text(report)
print(f"wrote {out}")
