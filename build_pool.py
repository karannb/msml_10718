"""Step 1: list every usable image of the four datasets with its pooled label, into data/pool.csv.

Training images are picked from this pool by clean.py (duplicates and test-set images removed).
"""

from pathlib import Path

import pandas as pd

from labels import INDOOR, PLANTDOC, WILTED, plantseg_label

RAW = Path("data/raw")
IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
rows = []


def images(folder):
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMG)


# Indoor Plant Disease Detection: its train / valid / test folders, without the pre-augmented `Augmented_*` copies.
for split in ["train", "valid", "test"]:
    for cls, label in INDOOR.items():
        for p in images(RAW / "indoor/indoor" / split / cls):
            if not p.name.startswith("Augmented_"):
                rows.append(dict(image=p, source="indoor", orig_label=cls, label=label))

# Healthy and Wilted Houseplant Images: no splits.
for cls, label in WILTED.items():
    for p in images(RAW / "wilted/houseplant_images" / cls):
        rows.append(dict(image=p, source="wilted", orig_label=cls, label=label))

# PlantSeg: all splits (the test set's 50 images are removed later, with their duplicates).
ps = RAW / "plantseg/plantseg"
meta = pd.read_csv(ps / "Metadata.csv", encoding="utf-8-sig")
split_dir = {"Training": "train", "Validation": "val", "Test": "test"}
for r in meta.to_dict("records"):
    rows.append(dict(image=ps / "images" / split_dir[r["Split"]] / r["Name"], source="plantseg",
                     orig_label=r["Disease"], label=plantseg_label(r["Disease"])))

# PlantDoc: train / test folders.
for split in ["train", "test"]:
    for cls, label in PLANTDOC.items():
        folder = RAW / "plantdoc" / split / cls
        if folder.exists():
            for p in images(folder):
                rows.append(dict(image=p, source="plantdoc", orig_label=cls, label=label))

df = pd.DataFrame(rows)
missing = ~df.image.map(Path.exists)
assert not missing.any(), df[missing].head()
df.to_csv("data/pool.csv", index=False)
print(pd.crosstab(df.label, df.source, margins=True))
