# Claude on resolved Reddit threads (claude-haiku-5-5, plain prompt, the 64 held-out test threads)

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here the 64 held-out test threads (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `plain`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`results/all-224px/head.npz`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `claude-haiku-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of the calls behind these numbers: $0.20.

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.61 [0.51, 0.70] | 29/20/15                              | 0.55 [0.46, 0.65] | 24/23/17                    |                12 |
| llm+classifier | 0.60 [0.50, 0.70] | 29/19/16                              | 0.60 [0.51, 0.70] | 26/25/13                    |                 9 |

## Classifier minus no classifier, paired by thread

| score        | all 64 threads      | without the borderline threads   | threads better / same / worse with classifier   |
|:-------------|:--------------------|:---------------------------------|:------------------------------------------------|
| diag_score   | -0.01 [-0.07, 0.06] | -0.01 [-0.07, 0.06]              | 7 / 48 / 9                                      |
| advice_score | 0.05 [-0.02, 0.12]  | 0.05 [-0.02, 0.12]               | 12 / 45 / 7                                     |

Per-thread grades and reasons: `results/llm/resolved-haiku-5-5/scores-test.csv`. Answers: `results/llm/resolved-haiku-5-5/answers/`.
