# 10-718: Machine Learning in Practice

## Data

```bash
mkdir -p data/raw && cd data/raw
curl -L -o indoor.zip   https://www.kaggle.com/api/v1/datasets/download/abdulahad0296/indoor-plant-disease-detection-dataset
curl -L -o wilted.zip   https://www.kaggle.com/api/v1/datasets/download/russellchan/healthy-and-wilted-houseplant-images
curl -L -o plantseg.zip https://zenodo.org/api/records/17719108/files/plantseg.zip/content
for z in indoor wilted plantseg; do unzip -q $z.zip -d $z && rm $z.zip; done
```

| Dataset | Images | Train / Valid / Test | Classes | In test set |
|---|---|---|---|---|
| [Indoor Plant Disease Detection](https://www.kaggle.com/datasets/abdulahad0296/indoor-plant-disease-detection-dataset) | 4,865 real (21,097 incl. `Augmented_*` copies) | 4,015 / 455 / 395 real | 16 (5 plants × condition) | 100 |
| [Healthy and Wilted Houseplants](https://www.kaggle.com/datasets/russellchan/healthy-and-wilted-houseplant-images) | 854 unique (904 files) | no splits | 2 (452 healthy / 452 wilted) | 50 |
| [PlantSeg](https://zenodo.org/records/17719108) | 7,774, each with a lesion mask | 5,367 / 846 / 1,561 | 115 diseases, 34 crops | 50 |

## Test set

`python build_testset.py` writes `data/testset.csv` (200 images, labels `healthy / watering / fungal_bacterial / pest / other`).
`data/gold_advice.json` is the advice answer key, from UMD and Clemson extension pages.
`data/curated.csv` is a hand-picked 12-image subset (clear examples of all 5 labels, from all 3 datasets) for manual evaluation, shown one by one in [curated.md](curated.md):

![Curated examples](assets/examples.jpg)

## LLM baseline (Gemini free tier)

Zero-shot classification of the 100 Indoor test images into the dataset's 16 native classes (plant + condition).

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # paste a free key from https://aistudio.google.com/apikey
python classify.py     # -> data/preds/<model>.csv (resumable)
python report.py       # -> reports/<model>.md
```

`llm.py` sends each image with a prompt listing the 16 classes and forces the answer to one of them. Set `GEMINI_MODEL` in `.env` to switch model.

Results: [gemini-3.1-flash-lite](reports/gemini-3.1-flash-lite.md): 61% accuracy (random: 6%), plant correct 81%, healthy vs. sick 93%.

## DINOv2 + linear head

A linear classifier on frozen [DINOv2](https://huggingface.co/facebook/dinov2-base) image embeddings, predicting the 5 pooled labels (plant type ignored).
Full explanation (labels, cleaning, results, limits): [reports/dinov2-head.md](reports/dinov2-head.md).
The label of each dataset's classes is in `labels.py`. Images live on `/data/user_data/mdrieux/msml_10718/raw` (`data/raw` links there); jobs run on Babel with `sbatch jobs/run.sbatch <script>`.

```bash
jobs/download.sh                       # the 3 datasets above + PlantDoc (github.com/pratikkayal/PlantDoc-Dataset)
python build_pool.py                   # -> data/pool.csv: every image with its pooled label (no Augmented_* copies)
python embed.py                        # DINOv2 embedding of every image (GPU)
python clean.py                        # -> data/trainval.csv: duplicates merged, copies of test images dropped, 85/15 split
python train_head.py --setting indoor  # -> results/indoor-224px/head.npz, reports/dinov2-head-indoor-224px.md
python train_head.py --setting all     # -> results/all-224px/head.npz,    reports/dinov2-head-all-224px.md
python predict.py results/all-224px/head.npz photo.jpg
```

Results on the 200-image test set (balanced accuracy):

| Trained on | 224 x 224 px | 448 x 448 px (`--image_size 448` in embed.py and train_head.py) |
|---|---|---|
| Indoor dataset only | [71%](reports/dinov2-head-indoor-224px.md) | [70%](reports/dinov2-head-indoor-448px.md) |
| All four datasets | [93%](reports/dinov2-head-all-224px.md) | [94%](reports/dinov2-head-all-448px.md) |
