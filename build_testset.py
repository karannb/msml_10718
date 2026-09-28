"""Step 0: sample the 200-image test set from data/raw/ into data/testset.csv."""

import random
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
rng = random.Random(10718)
rows = []

# Indoor Plant Disease Detection: 100 images, even across its 16 classes.
INDOOR = {
    "Aloe_Healthy": "healthy",
    "Cactus_Healthy": "healthy",
    "Money_Plant_Healthy": "healthy",
    "Snake_Plant_Healthy": "healthy",
    "Spider_Plant_Healthy": "healthy",
    "Snake_Plant_Leaf_Withering": "watering",  # judgment call
    "Aloe_Anthracnose": "fungal_bacterial",
    "Aloe_LeafSpot": "fungal_bacterial",
    "Aloe_Rust": "fungal_bacterial",
    "Snake_Plant_Anthracnose": "fungal_bacterial",
    "Spider_Plant_Fungal_leaf_spot": "fungal_bacterial",
    "Money_Plant_Bacterial_wilt_disease": "fungal_bacterial",
    "Cactus_Dactylopius_Opuntia": "pest",  # cochineal scale insect
    "Aloe_Sunburn": "other",
    "Money_Plant_Manganese_Toxicity": "other",
    "Spider_Plant_Leaf_Tip_Necrosis": "other",  # judgment call: salts/fluoride
}
for i, (cls, label) in enumerate(sorted(INDOOR.items())):
    # Held-out splits only, skipping the dataset's pre-augmented copies.
    pool = sorted(p for split in ["test", "valid"] for p in (RAW / "indoor/indoor" / split / cls).iterdir()
                  if not p.name.startswith("Augmented_"))
    for p in rng.sample(pool, 6 + (i < 4)):  # 16 classes * 6 + 4 = 100
        rows.append(dict(image=p, source="indoor", orig_label=cls, label=label))

# Healthy and Wilted Houseplant Images: 25 + 25.
for cls, label in [("healthy", "healthy"), ("wilted", "watering")]:
    for p in rng.sample(sorted((RAW / "wilted/houseplant_images" / cls).iterdir()), 25):
        rows.append(dict(image=p, source="wilted", orig_label=cls, label=label))

# PlantSeg: 50 from its test split, 10 per mask-ratio quintile (mild -> severe), one per disease per quintile.
ps = RAW / "plantseg/plantseg"
meta = pd.read_csv(ps / "Metadata.csv", encoding="utf-8-sig").query("Split == 'Test'")
meta["bin"] = pd.qcut(meta["Mask ratio"], 5, labels=False)
for _, grp in meta.groupby("bin"):
    grp = grp.sample(frac=1, random_state=rng.randrange(2**32)).drop_duplicates("Disease").head(10)
    for r in grp.to_dict("records"):
        virus = any(k in r["Disease"] for k in ["virus", "mosaic", "bunchy top", "leafroll"])
        rows.append(dict(
            image=ps / "images/test" / r["Name"],
            source="plantseg",
            orig_label=r["Disease"],
            label="other" if virus or r["Disease"] == "bell pepper blossom end rot" else "fungal_bacterial",
            mask=ps / "annotations/test" / r["Label file"],
            mask_ratio=r["Mask ratio"],
        ))

df = pd.DataFrame(rows)
df.to_csv("data/testset.csv", index=False)
print(pd.crosstab(df.label, df.source, margins=True))
