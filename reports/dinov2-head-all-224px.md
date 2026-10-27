# Linear head on frozen DINOv2, trained on: all four datasets

Task: classify a plant photo into 5 conditions (plant type ignored): `healthy`, `watering`, `fungal_bacterial`, `pest`, `other`.

## Model

- `facebook/dinov2-base` (ViT-B/14), frozen. Embedding $z$ = [CLS token ; mean of patch tokens] of the last layer, 1536 numbers.
  Image preprocessing: rotation flag of the file applied, shorter side resized to 256, center crop 224.
- Head: multinomial logistic regression on the standardized embedding, classes weighted by $1 / $ their frequency
  (scikit-learn `LogisticRegression(class_weight="balanced")`). Regularization C = 0.01, chosen from {0.001,0.003,0.01,0.03,0.1,0.3,1}
  by balanced accuracy on the validation images (90.4%).

## Data

Training images come from `data/trainval.csv` (`python build_pool.py`, then `python clean.py`): exact and near duplicates
merged to one image, groups containing a test image or with conflicting labels dropped, 15% kept for validation.

| label            |   ('indoor', 'train') |   ('indoor', 'val') |   ('plantdoc', 'train') |   ('plantdoc', 'val') |   ('plantseg', 'train') |   ('plantseg', 'val') |   ('wilted', 'train') |   ('wilted', 'val') |
|:-----------------|----------------------:|--------------------:|------------------------:|----------------------:|------------------------:|----------------------:|----------------------:|--------------------:|
| healthy          |                  1205 |                 213 |                     705 |                   124 |                       0 |                     0 |                   332 |                  58 |
| watering         |                   154 |                  27 |                       0 |                     0 |                       0 |                     0 |                   324 |                  57 |
| fungal_bacterial |                  1387 |                 245 |                    1280 |                   226 |                    5257 |                   928 |                     0 |                   0 |
| pest             |                   216 |                  38 |                       2 |                     0 |                       0 |                     0 |                     0 |                   0 |
| other            |                   679 |                 120 |                     107 |                    19 |                     481 |                    85 |                     0 |                   0 |

## Test set (`data/testset.csv`, 200 images, the same for every model)

Balanced accuracy = mean over the true labels of the share of their images predicted correctly.

|          |   images | accuracy   | balanced accuracy   |
|:---------|---------:|:-----------|:--------------------|
| all      |      200 | 88%        | 93%                 |
| indoor   |      100 | 80%        | 87%                 |
| plantseg |       50 | 100%       | 100%                |
| wilted   |       50 | 92%        | 92%                 |

Per label (all 200 images):

| label            |   n |   correct | recall   |
|:-----------------|----:|----------:|:---------|
| healthy          |  56 |        50 | 89%      |
| watering         |  31 |        30 | 97%      |
| fungal_bacterial |  82 |        65 | 79%      |
| pest             |   6 |         6 | 100%     |
| other            |  25 |        25 | 100%     |

Confusion matrix (rows = true label, columns = predicted):

|                  |   healthy |   watering |   fungal_bacterial |   pest |   other |
|:-----------------|----------:|-----------:|-------------------:|-------:|--------:|
| healthy          |        50 |          4 |                  1 |      0 |       1 |
| watering         |         0 |         30 |                  1 |      0 |       0 |
| fungal_bacterial |         4 |          1 |                 65 |      0 |      12 |
| pest             |         0 |          0 |                  0 |      6 |       0 |
| other            |         0 |          0 |                  0 |      0 |      25 |
