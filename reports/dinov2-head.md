# Plant condition classifier: a linear head on frozen DINOv2

**Goal.** A user takes a phone photo of a houseplant. The model says which of 5 conditions it shows, ignoring the plant species:

| Label | Meaning |
|---|---|
| `healthy` | no visible problem |
| `watering` | wilting or withering from too little or too much water |
| `fungal_bacterial` | leaf spots, rust, anthracnose, blight, rot, wilt disease |
| `pest` | visible insects or mites |
| `other` | anything else: sunburn, nutrient or mineral problems, viruses, tip necrosis |

The model only diagnoses. The advice for each label is in `data/gold_advice.json`.

## Model

1. **Image embedding.** `facebook/dinov2-base` (ViT-B/14, 86M parameters) stays frozen; it is never trained.
   - Before embedding, each photo is rotated according to its EXIF flag, its shorter side is resized to 256 px, and it is center-cropped to 224 x 224.
   - The embedding $z$ is the CLS token concatenated with the mean of the patch tokens of the last layer: 1536 numbers. This is the linear-probe input used in the DINOv2 paper.
2. **Head.** Multinomial logistic regression on the standardized embedding:
   - prediction: $\hat y = \arg\max_k (W \frac{z - \mu}{\sigma} + b)_k$;
   - classes are weighted by 1 / their frequency (`class_weight="balanced"`);
   - the regularization strength $C$ is picked from {0.001, ..., 1} by balanced accuracy on the validation images.

The head trains in seconds on CPU once the embeddings exist. Only computing the embeddings needs a GPU.

## Data

Four public datasets. Each dataset's classes map to the 5 labels in `labels.py`, the single place where that mapping lives:

| Dataset | What it is | Mapping |
|---|---|---|
| Indoor Plant Disease (Kaggle) | 5 houseplants x 16 conditions | e.g. `Aloe_Rust` → fungal_bacterial, `Cactus_Dactylopius_Opuntia` (cochineal) → pest, `Aloe_Sunburn` → other, `Snake_Plant_Leaf_Withering` → watering |
| Healthy & Wilted Houseplants (Kaggle) | healthy vs wilted | wilted → watering |
| PlantSeg (Zenodo) | 115 crop diseases | viruses and blossom end rot → other, everything else → fungal_bacterial |
| PlantDoc (GitHub) | 28 classes, web photos of 13 crops | plain "X leaf" → healthy, spider mites → pest, viruses → other, the rest → fungal_bacterial |

**Cleaning** (`clean.py`):

- Two images count as the same if their files are identical, or if their DINOv2 CLS embeddings have cosine similarity ≥ 0.96. Resized, re-encoded and lightly cropped copies get caught this way; the threshold was chosen by looking at pairs.
- Duplicates are grouped. A group is dropped if it contains a test image (so no copy of a test image is trained on) or if its members disagree on the label. Otherwise one image is kept.
- The Indoor dataset's `Augmented_*` copies are not used.
- The kept images are split 85% training / 15% validation, stratified by (dataset, label), seed 0.

Training images per label:

| Setting | healthy | watering | fungal_bacterial | pest | other | total |
|---|---:|---:|---:|---:|---:|---:|
| Indoor dataset only | 1,205 | 154 | 1,387 | 216 | 679 | 3,641 |
| All four datasets | 2,242 | 478 | 7,924 | 218 | 1,267 | 12,129 |

## Evaluation

All models are scored on the same 200-image test set, `data/testset.csv`: 100 Indoor, 50 Wilted and 50 PlantSeg images. None of these images, nor any duplicate of them, is used for training.

The headline number is **balanced accuracy**: the mean, over the 5 true labels, of the share of that label's images predicted correctly. Plain accuracy would reward a model that always predicts the most common label.

## Results

| Trained on | Image size | Balanced accuracy, all 200 | Indoor test images | Wilted test images | PlantSeg test images |
|---|---|---:|---:|---:|---:|
| Indoor dataset only | 224 px | 71% | 91% | 40% | 40% |
| All four datasets | 224 px | **93%** | 87% | **92%** | **100%** |
| Indoor dataset only | 448 px | 70% | 90% | 34% | 44% |
| All four datasets | 448 px | **94%** | **92%** | **92%** | 99% |

For comparison, the Gemini zero-shot baseline above reaches 61% on the Indoor dataset's 16 native classes.

- **Merging the datasets is what matters.** Trained on Indoor alone, the model fails on the other datasets' photos (40% on Wilted and on PlantSeg). With all four datasets it gets 92-100% there.
- **Doubling the resolution changes little** (93% → 94%) and costs 4x more compute. 224 px is the default.

Per-label recalls and confusion matrices are in `reports/dinov2-head-<setting>-<size>px.md`. Per-image predictions are in `results/<setting>-<size>px/test_predictions.csv`.

## Limits

- **This is not a test on new kinds of photos.** In the "all four" setting, every dataset in the test set is also in training. Real phone photos will look different, and the 93% will not carry over as is.
- **`pest` is narrow.** Almost all of its training images are cochineal on cactus (PlantDoc adds only 2 spider-mite photos), so the model has barely seen mealybugs, thrips or aphids.
- **The model is overconfident.** On a few real Reddit photos it gives wrong labels at about 99% probability. For example, it calls a cold-damaged Fatsia "watering". Its probabilities should not be shown to users as confidence.

Natural next steps:

1. Leave-one-dataset-out evaluation: train without a dataset, test on it.
2. Calibration, or an "unsure" answer for photos unlike the training data.
3. More real phone photos, above all of pests and watering problems.

## Reproduce

Run on the Babel cluster. `jobs/` has the `sbatch` wrappers, and the README has the commands in order:

1. `build_pool.py`
2. `embed.py`
3. `clean.py`
4. `train_head.py --setting indoor|all`
5. `predict.py`

The trained heads are in `results/*/head.npz` (a few hundred KB each), so `python predict.py results/all-224px/head.npz photo.jpg` works without retraining.
