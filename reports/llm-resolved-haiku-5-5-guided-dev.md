# Claude on resolved Reddit threads (claude-haiku-5-5, guided prompt, the 32 development threads)

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here the 32 development threads (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `guided`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`results/all-224px/head.npz`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `claude-haiku-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of the calls behind these numbers: $0.10.

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.61 [0.45, 0.75] | 16/7/9                                | 0.56 [0.41, 0.70] | 15/6/11                     |                 8 |
| llm+classifier | 0.66 [0.50, 0.80] | 18/6/8                                | 0.61 [0.47, 0.73] | 14/11/7                     |                 6 |

## Classifier minus no classifier, paired by thread

| score        | all 32 threads     | without the borderline threads   | threads better / same / worse with classifier   |
|:-------------|:-------------------|:---------------------------------|:------------------------------------------------|
| diag_score   | 0.05 [-0.03, 0.12] | 0.04 [-0.06, 0.13]               | 5 / 25 / 2                                      |
| advice_score | 0.05 [-0.05, 0.14] | 0.02 [-0.07, 0.11]               | 6 / 23 / 3                                      |

Per-thread grades and reasons: `results/llm/resolved-haiku-5-5-guided/scores-dev.csv`. Answers: `results/llm/resolved-haiku-5-5-guided/answers/`.
