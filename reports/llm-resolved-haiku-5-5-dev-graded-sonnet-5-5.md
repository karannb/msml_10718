# Claude on resolved Reddit threads (claude-haiku-5-5, plain prompt, the 32 development threads)

Data: `data/reddit/resolved/threads.csv`, threads where the poster said the advice worked; here the 32 development threads (split with
seed 0 in `eval_resolved.py`). The model under test sees only the post (its photos, title and the poster's text, the
`question` column) and is asked "What is wrong with my plant?" (`diagnose.py`, system prompt `plain`). Option
`llm+classifier` also gets the DINOv2 classifier's probabilities for each photo (`results/all-224px/head.npz`), with its 5 classes and a
warning that it is unreliable on phone photos.

Grading: `claude-sonnet-5-5` reads each answer, without knowing which option produced it, next to the thread's confirmed
problem (`problem`), the commenters' advice (`answer`) and the poster's outcome (`outcome`). Scores: diagnosis correct 1,
partial 0.5, wrong 0; advice that would have led to the same fix: yes 1, partial 0.5, no 0. With several answers per thread
(2), scores are averaged per thread first. Brackets: 95% bootstrap interval over threads. Cost of the calls behind these numbers: $0.33.

## Scores (higher is better)

| option   | diagnosis score   | diagnosis correct / partial / wrong   | advice score      | advice yes / partial / no   |   harmful answers |
|:---------|:------------------|:--------------------------------------|:------------------|:----------------------------|------------------:|
| llm      | 0.64 [0.53, 0.74] | 25/32/7                               | 0.68 [0.58, 0.77] | 28/31/5                     |                 4 |


Per-thread grades and reasons: `results/llm/resolved-haiku-5-5/scores-dev-sonnet-5-5.csv`. Answers: `results/llm/resolved-haiku-5-5/answers/`.
