# Zero-shot LLM baseline: `gemini-3.1-flash-lite`

Task: [Indoor Plant Disease Detection](https://www.kaggle.com/datasets/abdulahad0296/indoor-plant-disease-detection-dataset),
16 native classes (plant + condition), on the 100 Indoor images of `data/testset.csv`
(6-7 held-out images per class, fixed seed; see `build_testset.py`).

| Metric | Score |
|---|---|
| **Accuracy (16 classes)** | **61% (61/100)** |
| Balanced accuracy | 62% |
| Plant correct (5 plants) | 81% |
| Healthy vs. sick correct | 93% |

## Setup

- Model: `gemini-3.1-flash-lite` (Gemini API free tier), temperature 0, one image per call.
- Output constrained to one of the 16 class names (`text/x.enum` response schema), so every answer is a valid class.
- Prompt (`llm.py`):

```
You are a plant health expert. Look at the photo, identify the plant and its condition, and answer with exactly one class:
- Aloe_Healthy: aloe vera, no visible problem
- Aloe_Anthracnose: aloe vera with anthracnose
- Aloe_LeafSpot: aloe vera with leaf spot
- Aloe_Rust: aloe vera with rust
- Aloe_Sunburn: aloe vera with sunburn
- Cactus_Healthy: cactus, no visible problem
- Cactus_Dactylopius_Opuntia: cactus infested by Dactylopius opuntiae (cochineal scale insect)
- Money_Plant_Healthy: money plant (pothos), no visible problem
- Money_Plant_Bacterial_wilt_disease: money plant (pothos) with bacterial wilt
- Money_Plant_Manganese_Toxicity: money plant (pothos) with manganese toxicity
- Snake_Plant_Healthy: snake plant, no visible problem
- Snake_Plant_Anthracnose: snake plant with anthracnose
- Snake_Plant_Leaf_Withering: snake plant with leaf withering
- Spider_Plant_Healthy: spider plant, no visible problem
- Spider_Plant_Fungal_leaf_spot: spider plant with fungal leaf spot
- Spider_Plant_Leaf_Tip_Necrosis: spider plant with leaf tip necrosis
```

- Reproduce: `python classify.py --model gemini-3.1-flash-lite` then `python report.py --model gemini-3.1-flash-lite`.

## Comparison with random baselines

K = 16 classes; p_k = share of test images with true class k (6 or 7 images each, so p_k is 0.06 or 0.07).
Balanced accuracy = mean over classes of the per-class accuracy; any guesser that ignores the image scores 1/K on it.

| Predictor                                 | Expected accuracy   | Accuracy   | Balanced accuracy   |
|:------------------------------------------|:--------------------|:-----------|:--------------------|
| Uniform random: each class with prob. 1/K | 1/K                 | 6%         | 6%                  |
| Stratified random: class k with prob. p_k | sum_k p_k^2         | 6%         | 6%                  |
| Majority class: always `Aloe_Healthy`     | max_k p_k           | 7%         | 6%                  |
| `gemini-3.1-flash-lite`                   |                     | 61%        | 62%                 |

With n = 100 images the accuracy is uncertain by about ±5% (one standard deviation, sqrt(a(1-a)/n)).

## Per class

| label                              |   n |   correct | predictions                                                                                                                |
|:-----------------------------------|----:|----------:|:---------------------------------------------------------------------------------------------------------------------------|
| Aloe_Healthy                       |   7 |         6 | Aloe_Healthy 6, Cactus_Healthy 1                                                                                           |
| Aloe_Anthracnose                   |   7 |         0 | Aloe_LeafSpot 2, Snake_Plant_Anthracnose 2, Aloe_Sunburn 1, Snake_Plant_Leaf_Withering 1, Spider_Plant_Leaf_Tip_Necrosis 1 |
| Aloe_LeafSpot                      |   7 |         5 | Aloe_LeafSpot 5, Snake_Plant_Anthracnose 1, Aloe_Sunburn 1                                                                 |
| Aloe_Rust                          |   7 |         1 | Aloe_LeafSpot 2, Aloe_Healthy 2, Snake_Plant_Anthracnose 2, Aloe_Rust 1                                                    |
| Aloe_Sunburn                       |   6 |         2 | Snake_Plant_Leaf_Withering 3, Aloe_Sunburn 2, Aloe_Healthy 1                                                               |
| Cactus_Healthy                     |   6 |         3 | Cactus_Healthy 3, Cactus_Dactylopius_Opuntia 3                                                                             |
| Cactus_Dactylopius_Opuntia         |   6 |         6 | Cactus_Dactylopius_Opuntia 6                                                                                               |
| Money_Plant_Healthy                |   6 |         6 | Money_Plant_Healthy 6                                                                                                      |
| Money_Plant_Bacterial_wilt_disease |   6 |         2 | Money_Plant_Manganese_Toxicity 4, Money_Plant_Bacterial_wilt_disease 2                                                     |
| Money_Plant_Manganese_Toxicity     |   6 |         6 | Money_Plant_Manganese_Toxicity 6                                                                                           |
| Snake_Plant_Healthy                |   6 |         6 | Snake_Plant_Healthy 6                                                                                                      |
| Snake_Plant_Anthracnose            |   6 |         6 | Snake_Plant_Anthracnose 6                                                                                                  |
| Snake_Plant_Leaf_Withering         |   6 |         3 | Snake_Plant_Leaf_Withering 3, Snake_Plant_Anthracnose 3                                                                    |
| Spider_Plant_Healthy               |   6 |         3 | Spider_Plant_Healthy 3, Snake_Plant_Healthy 2, Snake_Plant_Leaf_Withering 1                                                |
| Spider_Plant_Fungal_leaf_spot      |   6 |         2 | Snake_Plant_Anthracnose 3, Spider_Plant_Fungal_leaf_spot 2, Spider_Plant_Leaf_Tip_Necrosis 1                               |
| Spider_Plant_Leaf_Tip_Necrosis     |   6 |         4 | Spider_Plant_Leaf_Tip_Necrosis 4, Snake_Plant_Leaf_Withering 2                                                             |

## Plant confusion

| true plant   |   Aloe |   Cactus |   Money_Plant |   Snake_Plant |   Spider_Plant |
|:-------------|-------:|---------:|--------------:|--------------:|---------------:|
| Aloe         |     23 |        1 |             0 |             9 |              1 |
| Cactus       |      0 |       12 |             0 |             0 |              0 |
| Money_Plant  |      0 |        0 |            18 |             0 |              0 |
| Snake_Plant  |      0 |        0 |             0 |            18 |              0 |
| Spider_Plant |      0 |        0 |             0 |             8 |             10 |

## Observations (run of 2026-09-29)

- Well above chance: 61% vs 6-7% for any image-blind guesser. Telling healthy from sick is easy (93%).
- Perfect on the visually distinct classes: cactus scale insects, money plant healthy / manganese toxicity, snake plant healthy / anthracnose.
- Most errors are the wrong plant, not the wrong condition: 9 aloe and 8 spider plant images are called snake plant (all long, narrow leaves; the aloe images are tight close-ups on black).
- Hardest classes: aloe anthracnose (0/7) and aloe rust (1/7), confused with other aloe spot diseases; money plant bacterial wilt is read as manganese toxicity (4/6).

## Next steps

- Rerun with a stronger free model (`gemini-3.7-flash`, 5 requests/min on the free tier).
- Let the model describe the image before answering (e.g. an `observation` field before the class).
