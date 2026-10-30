# eval_methodology.md metrics: claude-haiku-5-5, prompt guided-v2, on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $2.39). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    |
|:---------------------------------|:-----------------------|
| reference coverage               | 80/96 = 83% [75%, 89%] |
| diagnosis correct                | 54/96 = 56% [46%, 66%] |
| solved                           | 0/96 = 0% [0%, 4%]     |
| solved without the capacity rule | 43/96 = 45% [35%, 55%] |
| potential harm (grader)          | 12/96 = 12% [7%, 21%]  |
| harm flag (rules)                | 15/96 = 16% [10%, 24%] |
| false alarm (healthy threads)    | 2/5 = 40% [12%, 77%]   |
| within capacity                  | 1/96 = 1% [0%, 6%]     |
| actions per answer               | 8.6                    |
| USD per 1,000 answers            | 1.17                   |

Paired by thread (McNemar; for harmful, "correct" = harmful):

| this vs baseline            | metric   |   only_this_correct |   only_baseline_correct |     p |
|:----------------------------|:---------|--------------------:|------------------------:|------:|
| llm vs claude-haiku-5-5:llm | covered  |                   3 |                       4 | 1     |
| llm vs claude-haiku-5-5:llm | solved   |                   0 |                       0 | 1     |
| llm vs claude-haiku-5-5:llm | harmful  |                   4 |                      11 | 0.118 |

Agreement with the original Haiku grades (`grades/`): diagnosis 83%, advice 78%, harmful 88%.

Per-answer results: `results/llm/resolved-haiku-5-5-guided-v2/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-haiku-5-5-guided-v2/grades-opus-5-5/`.
