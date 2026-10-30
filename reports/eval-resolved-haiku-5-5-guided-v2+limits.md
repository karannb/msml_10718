# eval_methodology.md metrics: claude-haiku-5-5, prompt guided-v2+limits, on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $2.07). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    |
|:---------------------------------|:-----------------------|
| reference coverage               | 76/96 = 79% [70%, 86%] |
| diagnosis correct                | 51/96 = 53% [43%, 63%] |
| solved                           | 2/96 = 2% [1%, 7%]     |
| solved without the capacity rule | 44/96 = 46% [36%, 56%] |
| potential harm (grader)          | 15/96 = 16% [10%, 24%] |
| harm flag (rules)                | 9/96 = 9% [5%, 17%]    |
| false alarm (healthy threads)    | 2/5 = 40% [12%, 77%]   |
| within capacity                  | 7/96 = 7% [4%, 14%]    |
| actions per answer               | 6.6                    |
| USD per 1,000 answers            | 1.21                   |

Paired by thread (McNemar; for harmful, "correct" = harmful):

| this vs baseline                      | metric   |   only_this_correct |   only_baseline_correct |     p |
|:--------------------------------------|:---------|--------------------:|------------------------:|------:|
| llm vs claude-haiku-5-5-guided-v2:llm | covered  |                   2 |                       6 | 0.289 |
| llm vs claude-haiku-5-5-guided-v2:llm | solved   |                   2 |                       0 | 0.5   |
| llm vs claude-haiku-5-5-guided-v2:llm | harmful  |                   6 |                       3 | 0.508 |


Per-answer results: `results/llm/resolved-haiku-5-5-guided-v2+limits/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-haiku-5-5-guided-v2+limits/grades-opus-5-5/`.
