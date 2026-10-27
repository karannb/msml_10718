# Claude on 96 resolved Reddit threads, with and without the classifier (claude-haiku-5-5)

Data: `data/reddit/resolved/threads.csv`, 96 threads where the poster said the advice worked. The model under test sees only
the post (its photos, title and the poster's text, the `question` column) and is asked "What is wrong with my plant?"
(`diagnose.py`). Option `llm+classifier` also gets the DINOv2 classifier's probabilities for each photo
(`results/all-224px/head.npz`), with its 5 classes and a warning that it is unreliable on phone photos.

Grading: `claude-haiku-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of this run: $0.30.

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.59 [0.52, 0.67] | 40/34/22                              | 0.55 [0.47, 0.63] | 36/34/26                    |                19 |
| llm+classifier | 0.59 [0.51, 0.68] | 44/26/26                              | 0.58 [0.51, 0.66] | 38/36/22                    |                16 |

## Classifier minus no classifier, paired by thread

| score        | all 96 threads     | without the 5 borderline threads   | threads better / same / worse with classifier   |
|:-------------|:-------------------|:-----------------------------------|:------------------------------------------------|
| diag_score   | 0.00 [-0.05, 0.06] | -0.01 [-0.07, 0.04]                | 11 / 72 / 13                                    |
| advice_score | 0.03 [-0.03, 0.09] | 0.03 [-0.03, 0.09]                 | 18 / 64 / 14                                    |

Per-thread grades and reasons: `results/llm/resolved-haiku-5-5/scores.csv`. Answers: `results/llm/resolved-haiku-5-5/answers/`.
