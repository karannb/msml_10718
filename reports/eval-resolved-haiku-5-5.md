# eval_methodology.md metrics: claude-haiku-5-5 on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $5.02). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    | llm+classifier         |
|:---------------------------------|:-----------------------|:-----------------------|
| reference coverage               | 81/96 = 84% [76%, 90%] | 77/96 = 80% [71%, 87%] |
| diagnosis correct                | 40/96 = 42% [32%, 52%] | 48/96 = 50% [40%, 60%] |
| solved                           | 0/96 = 0% [0%, 4%]     | 0/96 = 0% [0%, 4%]     |
| solved without the capacity rule | 36/96 = 38% [28%, 47%] | 43/96 = 45% [35%, 55%] |
| potential harm (grader)          | 19/96 = 20% [13%, 29%] | 10/96 = 10% [6%, 18%]  |
| harm flag (rules)                | 18/96 = 19% [12%, 28%] | 10/96 = 10% [6%, 18%]  |
| false alarm (healthy threads)    | 2/5 = 40% [12%, 77%]   | 1/5 = 20% [4%, 62%]    |
| within capacity                  | 2/96 = 2% [1%, 7%]     | 2/96 = 2% [1%, 7%]     |
| actions per answer               | 9.1                    | 8.6                    |
| USD per 1,000 answers            | 1.16                   | 1.28                   |

Paired by thread (McNemar; for harmful, "correct" = harmful):

| this vs baseline                        | metric   |   only_this_correct |   only_baseline_correct |        p |
|:----------------------------------------|:---------|--------------------:|------------------------:|---------:|
| llm+classifier vs llm                   | covered  |                   2 |                       6 | 0.289    |
| llm+classifier vs llm                   | solved   |                   0 |                       0 | 1        |
| llm+classifier vs llm                   | harmful  |                   3 |                      12 | 0.0352   |
| llm vs claude-sonnet-5-5:llm            | covered  |                   0 |                       9 | 0.00391  |
| llm vs claude-sonnet-5-5:llm            | solved   |                   0 |                       0 | 1        |
| llm vs claude-sonnet-5-5:llm            | harmful  |                  11 |                       2 | 0.0225   |
| llm+classifier vs claude-sonnet-5-5:llm | covered  |                   0 |                      13 | 0.000244 |
| llm+classifier vs claude-sonnet-5-5:llm | solved   |                   0 |                       0 | 1        |
| llm+classifier vs claude-sonnet-5-5:llm | harmful  |                   4 |                       4 | 1        |

Agreement with the original Haiku grades (`grades/`): diagnosis 85%, advice 77%, harmful 86%.

Per-answer results: `results/llm/resolved-haiku-5-5/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-haiku-5-5/grades-opus-5-5/`.
