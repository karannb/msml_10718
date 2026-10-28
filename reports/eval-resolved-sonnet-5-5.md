# eval_methodology.md metrics: claude-sonnet-5-5 on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $5.45). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    | llm+classifier         |
|:---------------------------------|:-----------------------|:-----------------------|
| reference coverage               | 90/96 = 94% [87%, 97%] | 84/96 = 88% [79%, 93%] |
| diagnosis correct                | 52/96 = 54% [44%, 64%] | 45/96 = 47% [37%, 57%] |
| solved                           | 0/96 = 0% [0%, 4%]     | 0/96 = 0% [0%, 4%]     |
| solved without the capacity rule | 46/96 = 48% [38%, 58%] | 44/96 = 46% [36%, 56%] |
| potential harm (grader)          | 10/96 = 10% [6%, 18%]  | 14/96 = 15% [9%, 23%]  |
| harm flag (rules)                | 22/96 = 23% [16%, 32%] | 14/96 = 15% [9%, 23%]  |
| false alarm (healthy threads)    | 1/5 = 20% [4%, 62%]    | 1/5 = 20% [4%, 62%]    |
| within capacity                  | 1/96 = 1% [0%, 6%]     | 0/96 = 0% [0%, 4%]     |
| actions per answer               | 10.0                   | 9.5                    |
| USD per 1,000 answers            | 17.88                  | 18.76                  |

Paired by thread (McNemar; for harmful, "correct" = harmful):

| this vs baseline      | metric   |   only_this_correct |   only_baseline_correct |      p |
|:----------------------|:---------|--------------------:|------------------------:|-------:|
| llm+classifier vs llm | covered  |                   1 |                       7 | 0.0703 |
| llm+classifier vs llm | solved   |                   0 |                       0 | 1      |
| llm+classifier vs llm | harmful  |                   4 |                       0 | 0.125  |

Agreement with the original Haiku grades (`grades/`): diagnosis 77%, advice 79%, harmful 93%.

Per-answer results: `results/llm/resolved-sonnet-5-5/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-sonnet-5-5/grades-opus-5-5/`.
