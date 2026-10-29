# Claude on resolved Reddit threads (claude-haiku-5-5, plain prompt, the 32 development threads)

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here the 32 development threads (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `plain`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`results/all-224px/head.npz`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `claude-haiku-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. Brackets: 95% bootstrap
interval over threads. Cost of the calls behind these numbers: $0.10.

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.56 [0.44, 0.69] | 11/14/7                               | 0.55 [0.41, 0.69] | 12/11/9                     |                 7 |
| llm+classifier | 0.58 [0.42, 0.72] | 15/7/10                               | 0.55 [0.41, 0.69] | 12/11/9                     |                 7 |

## Classifier minus no classifier, paired by thread

| score        | all 32 threads     | without the borderline threads   | threads better / same / worse with classifier   |
|:-------------|:-------------------|:---------------------------------|:------------------------------------------------|
| diag_score   | 0.02 [-0.08, 0.12] | -0.02 [-0.11, 0.07]              | 4 / 24 / 4                                      |
| advice_score | 0.00 [-0.12, 0.12] | 0.00 [-0.11, 0.11]               | 6 / 19 / 7                                      |

Per-thread grades and reasons: `results/llm/resolved-haiku-5-5/scores-dev.csv`. Answers: `results/llm/resolved-haiku-5-5/answers/`.
