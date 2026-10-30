# eval_methodology.md metrics: claude-opus-5-5, prompt guided-v2+limits-high, on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $1.92). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    |
|:---------------------------------|:-----------------------|
| reference coverage               | 76/96 = 79% [70%, 86%] |
| diagnosis correct                | 50/96 = 52% [42%, 62%] |
| solved                           | 7/96 = 7% [4%, 14%]    |
| solved without the capacity rule | 41/96 = 43% [33%, 53%] |
| potential harm (grader)          | 15/96 = 16% [10%, 24%] |
| harm flag (rules)                | 17/96 = 18% [11%, 27%] |
| false alarm (healthy threads)    | 1/5 = 20% [4%, 62%]    |
| within capacity                  | 22/96 = 23% [16%, 32%] |
| actions per answer               | 5.1                    |
| USD per 1,000 answers            | 47.02                  |

Paired by thread (McNemar; for harmful, "correct" = harmful):

| this vs baseline                          | metric   |   only_this_correct |   only_baseline_correct |       p |
|:------------------------------------------|:---------|--------------------:|------------------------:|--------:|
| llm vs claude-opus-5-5-guided-v2-high:llm | covered  |                   1 |                      13 | 0.00183 |
| llm vs claude-opus-5-5-guided-v2-high:llm | solved   |                   7 |                       0 | 0.0156  |
| llm vs claude-opus-5-5-guided-v2-high:llm | harmful  |                   8 |                       1 | 0.0391  |


Per-answer results: `results/llm/resolved-opus-5-5-guided-v2+limits-high/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-opus-5-5-guided-v2+limits-high/grades-opus-5-5/`.
