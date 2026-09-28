# Zero-shot LLM baseline: `gemini-3.1-flash-lite`

**Accuracy: 62% (62/100)** on the indoor test images of `data/testset.csv`.
Without the 3 classes whose label mapping is a judgment call (`Snake_Plant_Leaf_Withering`, `Spider_Plant_Leaf_Tip_Necrosis`, `Money_Plant_Manganese_Toxicity`):
**74% (61/82)**.

## Setup

- Model: `gemini-3.1-flash-lite` (Gemini API free tier), temperature 0, one image per call, no plant name given.
- Output constrained to one of the 5 labels (`text/x.enum` response schema), so every answer is a valid label.
- Prompt (`llm.py`):

```
You are a plant health expert. Look at the photo of a plant and classify its main condition.
Answer with exactly one label:
- healthy: no visible problem.
- watering: wilting, drooping, withering or collapse caused by too little or too much water.
- fungal_bacterial: spots, lesions, rust, mildew, rot, blight or wilt caused by a fungus or bacterium.
- pest: insects, mites, scale or other animals on or damaging the plant.
- other: any other problem (sunburn, nutrient deficiency or toxicity, salt/fluoride tip burn, virus, physiological disorder).
```

- Reproduce: `python classify.py --model gemini-3.1-flash-lite` then `python report.py --model gemini-3.1-flash-lite`.

## Comparison with random baselines

K = 5 labels; p_k = share of test images with true label k (healthy 0.31, watering 0.06, fungal_bacterial 0.39, pest 0.06, other 0.18).
Balanced accuracy = mean over labels of the per-label accuracy; any guesser that ignores the image scores 1/K on it.

| Predictor                                 | Expected accuracy   | Accuracy   | Balanced accuracy   |
|:------------------------------------------|:--------------------|:-----------|:--------------------|
| Uniform random: each label with prob. 1/K | 1/K                 | 20%        | 20%                 |
| Stratified random: label k with prob. p_k | sum_k p_k^2         | 29%        | 20%                 |
| Majority class: always `fungal_bacterial` | max_k p_k           | 39%        | 20%                 |
| `gemini-3.1-flash-lite`                   |                     | 62%        | 54%                 |

With n = 100 images the accuracy is uncertain by about ±5% (one standard deviation, sqrt(a(1-a)/n)).

## Accuracy per label

| label            |   n |   correct | accuracy   |
|:-----------------|----:|----------:|:-----------|
| fungal_bacterial |  39 |        28 | 72%        |
| healthy          |  31 |        25 | 81%        |
| other            |  18 |         3 | 17%        |
| pest             |   6 |         6 | 100%       |
| watering         |   6 |         0 | 0%         |

## Confusion matrix

| true             |   fungal_bacterial |   healthy |   other |   pest |   watering |
|:-----------------|-------------------:|----------:|--------:|-------:|-----------:|
| fungal_bacterial |                 28 |         2 |       4 |      3 |          2 |
| healthy          |                  2 |        25 |       1 |      2 |          1 |
| other            |                  2 |         1 |       3 |      0 |         12 |
| pest             |                  0 |         0 |       0 |      6 |          0 |
| watering         |                  5 |         0 |       1 |      0 |          0 |

## Per original class

| orig_label                         | label            |   n |   correct | predictions                                        |
|:-----------------------------------|:-----------------|----:|----------:|:---------------------------------------------------|
| Aloe_Anthracnose                   | fungal_bacterial |   7 |         3 | other 3, fungal_bacterial 3, watering 1            |
| Aloe_Healthy                       | healthy          |   7 |         6 | healthy 6, pest 1                                  |
| Aloe_LeafSpot                      | fungal_bacterial |   7 |         5 | fungal_bacterial 5, other 1, healthy 1             |
| Aloe_Rust                          | fungal_bacterial |   7 |         5 | fungal_bacterial 5, pest 1, healthy 1              |
| Aloe_Sunburn                       | other            |   6 |         2 | watering 2, other 2, healthy 1, fungal_bacterial 1 |
| Cactus_Dactylopius_Opuntia         | pest             |   6 |         6 | pest 6                                             |
| Cactus_Healthy                     | healthy          |   6 |         2 | healthy 2, fungal_bacterial 2, other 1, pest 1     |
| Money_Plant_Bacterial_wilt_disease | fungal_bacterial |   6 |         4 | fungal_bacterial 4, pest 1, watering 1             |
| Money_Plant_Healthy                | healthy          |   6 |         6 | healthy 6                                          |
| Money_Plant_Manganese_Toxicity     | other            |   6 |         0 | watering 5, fungal_bacterial 1                     |
| Snake_Plant_Anthracnose            | fungal_bacterial |   6 |         6 | fungal_bacterial 6                                 |
| Snake_Plant_Healthy                | healthy          |   6 |         6 | healthy 6                                          |
| Snake_Plant_Leaf_Withering         | watering         |   6 |         0 | fungal_bacterial 5, other 1                        |
| Spider_Plant_Fungal_leaf_spot      | fungal_bacterial |   6 |         5 | fungal_bacterial 5, pest 1                         |
| Spider_Plant_Healthy               | healthy          |   6 |         5 | healthy 5, watering 1                              |
| Spider_Plant_Leaf_Tip_Necrosis     | other            |   6 |         1 | watering 5, other 1                                |

## Observations (run of 2026-09-28)

- The model beats the strongest image-blind guesser (always `fungal_bacterial`, 39%) by 23 points, and scores 54% balanced accuracy vs 20% for any guesser.
- Clear-cut classes are near perfect: cactus scale insects (pest), snake plant anthracnose, healthy snake and money plants.
- Most errors come from the 16 -> 5 label mapping in `build_testset.py`, not from what the model sees: leaf withering (mapped to `watering`) is read as disease, and leaf tip necrosis / manganese toxicity (mapped to `other`) are read as watering problems. These 3 classes hold 17 of the 38 errors.
- Real weaknesses: healthy cacti called diseased (2/6), aloe anthracnose (3/7) and aloe sunburn (2/6).
- The bare-label output gives the model no room to describe the image first, and it cannot abstain.

## Next steps

- Rerun with a stronger free model (`gemini-3.7-flash`, 5 requests/min on the free tier).
- Add a short `observation` field before the label, and make the label definitions match the mapping in `build_testset.py`.
- Run on the full 200-image test set once the Wilted and PlantSeg images are downloaded.
