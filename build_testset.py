"""Step 0: sample the 200-image test set from data/raw/ into data/testset.csv."""

import random
from pathlib import Path

import pandas as pd

from labels import INDOOR, WILTED, plantseg_label

RAW = Path("data/raw")
rng = random.Random(10718)
rows = []

# Indoor Plant Disease Detection: 100 images, even across its 16 classes.
for i, (cls, label) in enumerate(sorted(INDOOR.items())):
    # Held-out splits only, skipping the dataset's pre-augmented copies.
    pool = sorted(p for split in ["test", "valid"] for p in (RAW / "indoor/indoor" / split / cls).iterdir()
                  if not p.name.startswith("Augmented_"))
    for p in rng.sample(pool, 6 + (i < 4)):  # 16 classes * 6 + 4 = 100
        rows.append(dict(image=p, source="indoor", orig_label=cls, label=label))

# Healthy and Wilted Houseplant Images: 25 + 25.
for cls, label in WILTED.items():
    for p in rng.sample(sorted((RAW / "wilted/houseplant_images" / cls).iterdir()), 25):
        rows.append(dict(image=p, source="wilted", orig_label=cls, label=label))

# PlantSeg: 50 from its test split, 10 per mask-ratio quintile (mild -> severe), one per disease per quintile.
ps = RAW / "plantseg/plantseg"
meta = pd.read_csv(ps / "Metadata.csv", encoding="utf-8-sig").query("Split == 'Test'")
meta["bin"] = pd.qcut(meta["Mask ratio"], 5, labels=False)
for _, grp in meta.groupby("bin"):
    grp = grp.sample(frac=1, random_state=rng.randrange(2**32)).drop_duplicates("Disease").head(10)
    for r in grp.to_dict("records"):
        rows.append(dict(
            image=ps / "images/test" / r["Name"],
            source="plantseg",
            orig_label=r["Disease"],
            label=plantseg_label(r["Disease"]),
            mask=ps / "annotations/test" / r["Label file"],
            mask_ratio=r["Mask ratio"],
        ))

df = pd.DataFrame(rows)
df.to_csv("data/testset.csv", index=False)
print(pd.crosstab(df.label, df.source, margins=True))
