"""Step 2: write reports/<model>.md from data/preds/<model>.csv (Indoor dataset, 16 native classes).

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

d = pd.read_csv("data/testset.csv").query("source == 'indoor'")
d = d.assign(label=d.orig_label).merge(pd.read_csv(f"data/preds/{args.model}.csv"), on="image")
d["ok"] = d.label == d.pred

PLANTS = ["Aloe", "Cactus", "Money_Plant", "Snake_Plant", "Spider_Plant"]
plant = lambda c: next(p for p in PLANTS if c.startswith(p))  # noqa: E731
sick = lambda c: not c.endswith("Healthy")  # noqa: E731
plant_acc = (d.label.map(plant) == d.pred.map(plant)).mean()
sick_acc = (d.label.map(sick) == d.pred.map(sick)).mean()

# Guessers that never look at the image, for comparison.
n, K = len(d), len(llm.LABELS)
share = d.label.value_counts(normalize=True).reindex(llm.LABELS, fill_value=0)
acc = d.ok.mean()
balanced = d.groupby("label").ok.mean().mean()  # mean of per-class accuracies
baselines = pd.DataFrame(
    [
        ["Uniform random: each class with prob. 1/K", "1/K", 1 / K, 1 / K],
        ["Stratified random: class k with prob. p_k", "sum_k p_k^2", (share ** 2).sum(), 1 / K],
        [f"Majority class: always `{share.idxmax()}`", "max_k p_k", share.max(), 1 / K],
        [f"`{args.model}`", "", acc, balanced],
    ],
    columns=["Predictor", "Expected accuracy", "Accuracy", "Balanced accuracy"],
)
for c in ["Accuracy", "Balanced accuracy"]:
    baselines[c] = baselines[c].map("{:.0%}".format)

per_class = d.groupby("label").agg(
    n=("ok", "size"), correct=("ok", "sum"),
    predictions=("pred", lambda s: ", ".join(f"{k} {v}" for k, v in s.value_counts().items())))
per_class = per_class.reindex([c for c in llm.LABELS if c in per_class.index]).reset_index()
confusion = pd.crosstab(d.label.map(plant), d.pred.map(plant), rownames=["true plant"], colnames=["predicted plant"])

report = f"""# Zero-shot LLM baseline: `{args.model}`

Task: [Indoor Plant Disease Detection](https://www.kaggle.com/datasets/abdulahad0296/indoor-plant-disease-detection-dataset),
{K} native classes (plant + condition), on the {n} Indoor images of `data/testset.csv`
(6-7 held-out images per class, fixed seed; see `build_testset.py`).

| Metric | Score |
|---|---|
| **Accuracy (16 classes)** | **{acc:.0%} ({d.ok.sum()}/{n})** |
| Balanced accuracy | {balanced:.0%} |
| Plant correct (5 plants) | {plant_acc:.0%} |
| Healthy vs. sick correct | {sick_acc:.0%} |

## Setup

- Model: `{args.model}` (Gemini API free tier), temperature 0, one image per call.
- Output constrained to one of the {K} class names (`text/x.enum` response schema), so every answer is a valid class.
- Prompt (`llm.py`):

```
{llm.PROMPT}
```

- Reproduce: `python classify.py --model {args.model}` then `python report.py --model {args.model}`.

## Comparison with random baselines

K = {K} classes; p_k = share of test images with true class k (6 or 7 images each, so p_k is 0.06 or 0.07).
Balanced accuracy = mean over classes of the per-class accuracy; any guesser that ignores the image scores 1/K on it.

{baselines.to_markdown(index=False)}

With n = {n} images the accuracy is uncertain by about ±{(acc * (1 - acc) / n) ** 0.5:.0%} (one standard deviation, sqrt(a(1-a)/n)).

## Per class

{per_class.to_markdown(index=False)}

## Plant confusion

{confusion.to_markdown()}
"""
out = Path("reports") / f"{args.model}.md"
out.parent.mkdir(exist_ok=True)
notes = out.read_text().split("\n## Observations", 1) if out.exists() else []
if len(notes) == 2:  # keep hand-written notes when regenerating
    report = report.rstrip() + "\n\n## Observations" + notes[1]
out.write_text(report)
print(f"wrote {out}")
