# Claude on resolved Reddit threads (claude-haiku-5-5, guided-v2 prompt, web search, the 64 held-out test threads)

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here the 64 held-out test threads (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `guided-v2`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`results/all-224px/head.npz`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `claude-sonnet-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. With several answers per thread
(2), scores are averaged per thread first. Brackets: 95% bootstrap interval over threads. Cost of the calls behind these numbers: $6.82.

Web search: the answering model could run up to 3 searches per answer (`web_search` tool; Reddit, its image hosts and Reddit mirrors/archives blocked). It ran 1.7 per answer on average. Answers whose results include a page that may be the thread itself (blocked domain, or a title close to the post's): 9 of 256 (listed under `possible_leaks` in each answer file).

## Scores (higher is better)

| option         | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm            | 0.68 [0.59, 0.77] | 68/39/21                              | 0.61 [0.51, 0.70] | 57/41/30                    |                22 |
| llm+classifier | 0.69 [0.61, 0.77] | 67/43/18                              | 0.64 [0.55, 0.72] | 57/49/22                    |                18 |

## Classifier minus no classifier, paired by thread

| score        | all 64 threads     | without the borderline threads   | threads better / same / worse with classifier   |
|:-------------|:-------------------|:---------------------------------|:------------------------------------------------|
| diag_score   | 0.01 [-0.03, 0.05] | 0.01 [-0.03, 0.05]               | 9 / 46 / 9                                      |
| advice_score | 0.03 [-0.02, 0.08] | 0.03 [-0.02, 0.08]               | 16 / 37 / 11                                    |

Per-thread grades and reasons: `results/llm/resolved-haiku-5-5-guided-v2-search/scores-test-sonnet-5-5.csv`. Answers: `results/llm/resolved-haiku-5-5-guided-v2-search/answers/`.
