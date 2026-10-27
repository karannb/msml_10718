"""Step 3: remove duplicates and test-set images from the pool, then split it into train / validation (data/trainval.csv).

Two images are duplicates if their files are identical (same md5) or their DINOv2 CLS embeddings have cosine
similarity >= --threshold (resized, re-encoded or lightly cropped copies). Duplicates are grouped (connected
components); then each group
  - is dropped if any member is a test-set image (so no copy of a test image is trained on),
  - is dropped if its members disagree on the pooled label,
  - otherwise keeps one image (the first path in sorted order).
The kept images are split 85% / 15% into train / validation, stratified by (source, label), seed 0.
"""

import argparse
import os

import numpy as np
import pandas as pd
import torch
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from embed import features_path

p = argparse.ArgumentParser()
p.add_argument("--threshold", type=float, default=0.96)
p.add_argument("--val_frac", type=float, default=0.15)
p.add_argument("--inspect", action="store_true", help="only print near-duplicate statistics and save example pairs")
args = p.parse_args()

F = np.load(features_path(224))  # duplicates are found once, at the default resolution
pool = pd.read_csv("data/pool.csv")
test = pd.read_csv("data/testset.csv")
print(f"pool: {len(pool)} images; unreadable: {list(F['unreadable'])}")

# One row per file: the pool, plus the test images (which are also in the pool except PlantSeg's).
df = pd.concat([pool, test[pool.columns]]).drop_duplicates("image").reset_index(drop=True)
df["in_test"] = df.image.isin(set(test.image))
idx = {p: i for i, p in enumerate(F["image"])}
df = df[df.image.isin(idx)].reset_index(drop=True)
rows = np.array([idx[p] for p in df.image])
md5 = F["md5"][rows]
cls = torch.nn.functional.normalize(torch.tensor(F["feat"][rows, :768]).cuda(), dim=1)  # CLS part of the embedding

# Pairs of near-duplicates, by blocks of 4096 rows.
I, J, S = [], [], []
nn_sim = np.zeros(len(df))
for a in range(0, len(df), 4096):
    s = cls[a:a + 4096] @ cls.T
    s[torch.arange(s.shape[0]), torch.arange(a, a + s.shape[0])] = -1
    nn_sim[a:a + 4096] = s.max(1).values.cpu().numpy()
    i, j = torch.nonzero(s >= min(args.threshold, 0.90), as_tuple=True)
    I.append((i + a).cpu().numpy()); J.append(j.cpu().numpy()); S.append(s[i, j].cpu().numpy())
I, J, S = np.concatenate(I), np.concatenate(J), np.concatenate(S)

if args.inspect:
    print("nearest-neighbour cosine similarity, quantiles:", np.round(np.quantile(nn_sim, [.5, .9, .95, .99]), 3))
    for t in [0.90, 0.92, 0.94, 0.95, 0.96, 0.98, 0.99]:
        print(f"share of images with a neighbour >= {t}: {np.mean(nn_sim >= t):.3f}")
    # Save 8 random pairs per similarity band, for looking at them.
    from PIL import Image
    rng = np.random.default_rng(0)
    os.makedirs("data/dup_examples", exist_ok=True)
    for lo, hi in [(0.90, 0.92), (0.92, 0.94), (0.94, 0.96), (0.96, 0.98), (0.98, 1.01)]:
        k = np.nonzero((S >= lo) & (S < hi) & (I < J))[0]
        if len(k) == 0:
            continue
        pick = rng.choice(k, size=min(8, len(k)), replace=False)
        sheet = Image.new("RGB", (2 * 160, 160 * len(pick)), "white")
        for r, q in enumerate(pick):
            for c, n in enumerate([I[q], J[q]]):
                im = Image.open(df.image[n]).convert("RGB")
                im.thumbnail((158, 158))
                sheet.paste(im, (c * 160, r * 160))
            print(f"band {lo:.2f}-{hi:.2f} row {r}: {S[q]:.3f} {df.source[I[q]]}/{df.orig_label[I[q]]} | {df.source[J[q]]}/{df.orig_label[J[q]]}")
        sheet.save(f"data/dup_examples/sim_{lo:.2f}_{hi:.2f}.jpg")
    raise SystemExit

# Duplicate groups: identical files or cosine >= threshold.
keep = S >= args.threshold
edges_i, edges_j = list(I[keep]), list(J[keep])
first = pd.Series(range(len(df))).groupby(md5).transform("first").to_numpy()
edges_i += list(range(len(df))); edges_j += list(first)
n_groups, group = connected_components(coo_matrix((np.ones(len(edges_i)), (edges_i, edges_j)), shape=(len(df),) * 2), directed=False)
df["group"] = group
g = df.groupby("group")
touches_test = g.in_test.transform("any")
mixed = g.label.transform("nunique") > 1
size = g.image.transform("size")

clean = df[~touches_test & ~mixed].sort_values("image").drop_duplicates("group")
report = pd.DataFrame({
    "images in pool": df[~df.in_test].groupby("source").size(),
    "in a duplicate group of size > 1": df[~df.in_test & (size > 1)].groupby("source").size(),
    "dropped: copy of a test image": df[~df.in_test & touches_test].groupby("source").size(),
    "dropped: group with mixed labels": df[~df.in_test & ~touches_test & mixed].groupby("source").size(),
    "kept (one per group)": clean.groupby("source").size(),
}).fillna(0).astype(int)
print(report.to_string())

# Train / validation split, stratified by (source, label).
rng = np.random.default_rng(0)
clean["split"] = "train"
for _, grp in clean.groupby(["source", "label"]):
    n_val = int(round(args.val_frac * len(grp)))
    clean.loc[rng.choice(grp.index, size=n_val, replace=False), "split"] = "val"
clean = clean[["image", "source", "orig_label", "label", "split"]].sort_values(["source", "image"])
clean.to_csv("data/trainval.csv", index=False)
print(pd.crosstab([clean.source, clean.label], clean.split, margins=True).to_string())
