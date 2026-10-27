# Linear head on frozen DINOv2 (448 x 448 px), trained on: indoor dataset only

Task: classify a plant photo into 5 conditions (plant type ignored): `healthy`, `watering`, `fungal_bacterial`, `pest`, `other`.

## Model

- `facebook/dinov2-base` (ViT-B/14), frozen. Embedding $z$ = [CLS token ; mean of patch tokens] of the last layer, 1536 numbers.
  Image preprocessing: rotation flag of the file applied, shorter side resized to 512, center crop 448.
- Head: multinomial logistic regression on the standardized embedding, classes weighted by $1 / $ their frequency
  (scikit-learn `LogisticRegression(class_weight="balanced")`). Regularization C = 0.03, chosen from {0.001,0.003,0.01,0.03,0.1,0.3,1}
  by balanced accuracy on the validation images (90.1%).

## Data

Training images come from `data/trainval.csv` (`python build_pool.py`, then `python clean.py`): exact and near duplicates
merged to one image, groups containing a test image or with conflicting labels dropped, 15% kept for validation.

| label            |   ('indoor', 'train') |   ('indoor', 'val') |
|:-----------------|----------------------:|--------------------:|
| healthy          |                  1205 |                 213 |
| watering         |                   154 |                  27 |
| fungal_bacterial |                  1387 |                 245 |
| pest             |                   216 |                  38 |
| other            |                   679 |                 120 |

## Test set (`data/testset.csv`, 200 images, the same for every model)

Balanced accuracy = mean over the true labels of the share of their images predicted correctly.

|          |   images | accuracy   | balanced accuracy   |
|:---------|---------:|:-----------|:--------------------|
| all      |      200 | 72%        | 70%                 |
| indoor   |      100 | 88%        | 90%                 |
| plantseg |       50 | 76%        | 44%                 |
| wilted   |       50 | 34%        | 34%                 |

Per label (all 200 images):

| label            |   n |   correct | recall   |
|:-----------------|----:|----------:|:---------|
| healthy          |  56 |        47 | 84%      |
| watering         |  31 |         5 | 16%      |
| fungal_bacterial |  82 |        69 | 84%      |
| pest             |   6 |         6 | 100%     |
| other            |  25 |        16 | 64%      |

Confusion matrix (rows = true label, columns = predicted):

|                  |   healthy |   watering |   fungal_bacterial |   pest |   other |
|:-----------------|----------:|-----------:|-------------------:|-------:|--------:|
| healthy          |        47 |          0 |                  6 |      2 |       1 |
| watering         |        14 |          5 |                  6 |      0 |       6 |
| fungal_bacterial |         6 |          2 |                 69 |      0 |       5 |
| pest             |         0 |          0 |                  0 |      6 |       0 |
| other            |         1 |          0 |                  8 |      0 |      16 |
