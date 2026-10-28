# Claude on 96 resolved Reddit threads, with and without the classifier (claude-sonnet-5-5)

Data: `data/reddit/resolved/threads.csv`, 96 threads where the poster said the advice worked. The model under test sees only
the post (its photos, title and the poster's text, the `question` column) and is asked "What is wrong with my plant?"
(`diagnose.py`). Option `llm+classifier` also gets the DINOv2 classifier's probabilities for each photo
(`results/all-224px/head.npz`), with its 5 classes and a warning that it is unreliable on phone photos.

Grading: `claude-haiku-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of this run: $3.58.

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.62 [0.55, 0.70] | 42/36/18                              | 0.65 [0.57, 0.71] | 42/40/14                    |                14 |
| llm+classifier | 0.57 [0.49, 0.65] | 37/35/24                              | 0.60 [0.52, 0.68] | 39/37/20                    |                16 |

## Classifier minus no classifier, paired by thread

| score        | all 96 threads      | without the 5 borderline threads   | threads better / same / worse with classifier   |
|:-------------|:--------------------|:-----------------------------------|:------------------------------------------------|
| diag_score   | -0.06 [-0.12, 0.01] | -0.05 [-0.12, 0.02]                | 11 / 66 / 19                                    |
| advice_score | -0.05 [-0.11, 0.02] | -0.03 [-0.09, 0.03]                | 11 / 68 / 17                                    |

Per-thread grades and reasons: `results/llm/resolved-sonnet-5-5/scores.csv`. Answers: `results/llm/resolved-sonnet-5-5/answers/`.
