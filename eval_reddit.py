"""Scores both trained heads on the Reddit cases: data/reddit/cases.csv, first post image saved as data/reddit/images/<case>.<ext>.

Cases without a pooled label (no reliable reference) get predictions but no score. Writes reports/reddit.md.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModel

from embed import MODEL, embed, load, processor

cases = pd.read_csv("data/reddit/cases.csv", dtype=str)
cases["image"] = [next(iter(sorted(Path("data/reddit/images").glob(f"{c}.*"))), None) for c in cases.case]
missing = cases[cases.image.isna()].case.tolist()
cases = cases.dropna(subset=["image"]).reset_index(drop=True)

model = AutoModel.from_pretrained(MODEL).cuda().eval()
NAMES = {"indoor": "Indoor only", "all": "All four datasets"}
heads = sorted(Path("results").glob("*px/head.npz"), key=lambda p: (int(p.parent.name.split("-")[1][:-2]), p.parent.name))
columns = []
for path in heads:
    head = np.load(path, allow_pickle=True)
    setting, size = path.parent.name.split("-")
    proc = processor(int(head["image_size"]))
    with torch.autocast("cuda", dtype=torch.bfloat16):
        z = embed(model, torch.stack([load(p, proc) for p in cases.image]).cuda()).float().cpu().numpy()
    logits = ((z - head["mu"]) / head["sd"]) @ head["W"].T + head["b"]
    prob = np.exp(logits - logits.max(1, keepdims=True))
    prob /= prob.sum(1, keepdims=True)
    order = np.argsort(-prob, axis=1)
    name = f"{NAMES[setting]}, {size[:-2]} px"
    columns.append(name)
    cases[name] = [f"{head['labels'][o[0]]} {p[o[0]]:.0%} (then {head['labels'][o[1]]} {p[o[1]]:.0%})" for o, p in zip(order, prob)]
    cases[name + " correct"] = [head["labels"][o[0]] == l if isinstance(l, str) else None for o, l in zip(order, cases.label)]

scored = cases.dropna(subset=["label"])
with open("reports/reddit.md", "w") as f:
    f.write("# Reddit cases (phone photos, independent of all training data)\n\n")
    f.write("First image of each post; reference diagnosis from the Reddit thread (not expert-confirmed). "
            "Label = the reference mapped to the 5 pooled labels; blank when the thread establishes no cause.\n\n")
    if missing:
        f.write(f"Missing images (not scored): cases {', '.join(missing)}.\n\n")
    for name in columns:
        f.write(f"- {name}: {int(scored[name + ' correct'].sum())} / {len(scored)} cases with a label predicted correctly\n")
    f.write("\n" + cases[["case", "reference", "label"] + columns].fillna("").to_markdown(index=False) + "\n")
print(open("reports/reddit.md").read())
