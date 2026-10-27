"""Step 4: train a linear classifier (multinomial logistic regression) on frozen DINOv2 embeddings.

    python train_head.py --setting indoor   # train on the Indoor dataset only
    python train_head.py --setting all      # train on all four datasets
    add --image_size 448 to use the 448 x 448 embeddings (python embed.py --image_size 448) instead of 224 x 224

Both settings use the same 5 pooled labels, the same cleaned train / validation split (data/trainval.csv, Indoor rows
only for `indoor`), pick the regularization C on their validation images, and are scored on the same 200-image
test set (data/testset.csv). Writes results/<setting>-<size>px/{head.npz,test_predictions.csv} and reports/dinov2-head-<setting>-<size>px.md.
"""

import argparse
import os

import matplotlib
import nb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix

from embed import MODEL, embed, features_path  # noqa: F401  (embed is a core function of this algorithm)
from labels import LABELS

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--setting", choices=["indoor", "all"], required=True)
p.add_argument("--image_size", type=int, default=224)
p.add_argument("--C_grid", default="0.001,0.003,0.01,0.03,0.1,0.3,1")
cfg = p.parse_args()
TITLES = {"indoor": "Indoor dataset only", "all": "All four datasets"}


@nb.core
def fit_head(z, y, C):
    """Standardize each embedding coordinate, then multinomial logistic regression with class-balanced weights."""
    mu, sd = z.mean(0), z.std(0) + 1e-6
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000).fit((z - mu) / sd, y)
    return dict(mu=mu, sd=sd, W=clf.coef_, b=clf.intercept_, labels=clf.classes_)


@nb.core
def predict(head, z):
    """Label with the largest score W (z - mu) / sd + b."""
    return head["labels"][np.argmax(((z - head["mu"]) / head["sd"]) @ head["W"].T + head["b"], axis=1)]


def scores(y, yhat):
    return dict(acc=accuracy_score(y, yhat), bal_acc=balanced_accuracy_score(y, yhat))


F = np.load(features_path(cfg.image_size))
feat = dict(zip(F["image"], F["feat"]))
tv = pd.read_csv("data/trainval.csv")
if cfg.setting == "indoor":
    tv = tv[tv.source == "indoor"]
test = pd.read_csv("data/testset.csv")
Z = {s: np.stack([feat[i] for i in d.image]) for s, d in [("train", tv[tv.split == "train"]), ("val", tv[tv.split == "val"]), ("test", test)]}
Y = {"train": tv[tv.split == "train"].label.to_numpy(), "val": tv[tv.split == "val"].label.to_numpy(), "test": test.label.to_numpy()}
grid = [float(c) for c in cfg.C_grid.split(",")]
config = dict(setting=cfg.setting, image_size=cfg.image_size, backbone=MODEL, embedding="cls+mean_patch", n_train=len(Y["train"]), n_val=len(Y["val"]),
              sources=",".join(sorted(tv.source.unique())), C_grid=cfg.C_grid, class_weight="balanced", val_frac=0.15, dup_threshold=0.96)

run = nb.start(
    subproject="training-data",
    title=f"{TITLES[cfg.setting]}, {cfg.image_size} px",
    formula=r"$\hat y = \arg\max_k (W \frac{z - \mu}{\sigma} + b)_k$, $z = \mathrm{DINOv2}(x)$ frozen, trained on \cfg{sources} ($n = \cfg{n_train}$)",
    algo="dinov2-linear-head",
    config=config,
    question="Does a linear head on frozen DINOv2 embeddings, trained on all four plant datasets instead of the Indoor dataset only, "
             "classify the 5 pooled conditions better on a fixed test set of 200 photos from three datasets?",
    baseline=cfg.setting == "indoor" and cfg.image_size == 224,  # the reference run; other runs are compared with it
)

# Choose C on the validation images (balanced accuracy).
best = None
for k, C in enumerate(grid):
    head = fit_head(Z["train"], Y["train"], C)
    v = scores(Y["val"], predict(head, Z["val"]))
    run.log(step=k, val_bal_acc=v["bal_acc"], val_acc=v["acc"], train_bal_acc=scores(Y["train"], predict(head, Z["train"]))["bal_acc"])
    print(f"C={C:g}: validation balanced accuracy {v['bal_acc']:.3f}", flush=True)
    if best is None or v["bal_acc"] > best[0]:
        best = (v["bal_acc"], C, head)
val_bal_acc, C, head = best

# Score on the fixed test set: all 200 images, then per source dataset.
test["pred"] = predict(head, Z["test"])
summary = {f"test_{k}": v for k, v in scores(test.label, test.pred).items()}
for src, d in test.groupby("source"):
    summary.update({f"test_{k}_{src}": v for k, v in scores(d.label, d.pred).items()})
summary.update(val_bal_acc=val_bal_acc, C=C)

name = f"{cfg.setting}-{cfg.image_size}px"
out = f"results/{name}"
os.makedirs(out, exist_ok=True)
np.savez(f"{out}/head.npz", **head, C=C, backbone=MODEL, image_size=cfg.image_size)
test[["image", "source", "orig_label", "label", "pred"]].to_csv(f"{out}/test_predictions.csv", index=False)

cm = pd.DataFrame(confusion_matrix(test.label, test.pred, labels=LABELS), index=LABELS, columns=LABELS)
fig, ax = plt.subplots(figsize=(5, 4.2))
ax.imshow(cm.to_numpy() / np.maximum(cm.to_numpy().sum(1, keepdims=True), 1), cmap="Blues", vmin=0, vmax=1)
for (i, j), n in np.ndenumerate(cm.to_numpy()):
    ax.text(j, i, n, ha="center", va="center", fontsize=9)
ax.set_xticks(range(5), LABELS, rotation=30, ha="right"); ax.set_yticks(range(5), LABELS)
ax.set_xlabel("predicted"); ax.set_ylabel("true"); ax.set_title(f"{TITLES[cfg.setting]}, {cfg.image_size} px: test set (200 images)")
run.figure("confusion", fig)

per_class = pd.DataFrame({
    "n": test.groupby("label").size(),
    "correct": test[test.label == test.pred].groupby("label").size(),
}).reindex(LABELS).fillna(0).astype(int)
per_class["recall"] = (per_class.correct / per_class.n.clip(lower=1)).map("{:.0%}".format)
per_source = pd.DataFrame({src: {"images": len(d), "accuracy": f"{accuracy_score(d.label, d.pred):.0%}",
                                 "balanced accuracy": f"{balanced_accuracy_score(d.label, d.pred):.0%}"}
                           for src, d in [("all", test)] + list(test.groupby("source"))}).T
counts = pd.crosstab(tv.label, [tv.source, tv.split]).reindex(LABELS).fillna(0).astype(int)
with open(f"reports/dinov2-head-{name}.md", "w") as f:
    f.write(f"""# Linear head on frozen DINOv2 ({cfg.image_size} x {cfg.image_size} px), trained on: {TITLES[cfg.setting].lower()}

Task: classify a plant photo into 5 conditions (plant type ignored): {", ".join(f"`{l}`" for l in LABELS)}.

## Model

- `{MODEL}` (ViT-B/14), frozen. Embedding $z$ = [CLS token ; mean of patch tokens] of the last layer, 1536 numbers.
  Image preprocessing: rotation flag of the file applied, shorter side resized to {cfg.image_size * 256 // 224}, center crop {cfg.image_size}.
- Head: multinomial logistic regression on the standardized embedding, classes weighted by $1 / $ their frequency
  (scikit-learn `LogisticRegression(class_weight="balanced")`). Regularization C = {C:g}, chosen from {{{cfg.C_grid}}}
  by balanced accuracy on the validation images ({val_bal_acc:.1%}).

## Data

Training images come from `data/trainval.csv` (`python build_pool.py`, then `python clean.py`): exact and near duplicates
merged to one image, groups containing a test image or with conflicting labels dropped, 15% kept for validation.

{counts.to_markdown()}

## Test set (`data/testset.csv`, 200 images, the same for every model)

Balanced accuracy = mean over the true labels of the share of their images predicted correctly.

{per_source.to_markdown()}

Per label (all 200 images):

{per_class.to_markdown()}

Confusion matrix (rows = true label, columns = predicted):

{cm.to_markdown()}
""")
print(open(f"reports/dinov2-head-{name}.md").read())
run.finish(**summary)
