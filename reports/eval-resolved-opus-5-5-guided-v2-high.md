# eval_methodology.md metrics: claude-opus-5-5, prompt guided-v2-high, on the 96 resolved Reddit threads

Answers from `eval_resolved.py`, graded by `claude-opus-5-5` with `prompts/resolved_grader.txt` (`score_resolved.py`;
grading cost $2.41). Solved = advice "yes", not harmful, at most 4 short actions (under 15 min/day, at most $15).
5 threads are healthy plants. Brackets: 95% Wilson interval.

|                                  | llm                    |
|:---------------------------------|:-----------------------|
| reference coverage               | 88/96 = 92% [84%, 96%] |
| diagnosis correct                | 51/96 = 53% [43%, 63%] |
| solved                           | 0/96 = 0% [0%, 4%]     |
| solved without the capacity rule | 58/96 = 60% [50%, 70%] |
| potential harm (grader)          | 8/96 = 8% [4%, 16%]    |
| harm flag (rules)                | 21/96 = 22% [15%, 31%] |
| false alarm (healthy threads)    | 0/5 = 0% [-0%, 43%]    |
| within capacity                  | 0/96 = 0% [0%, 4%]     |
| actions per answer               | 8.4                    |
| USD per 1,000 answers            | 47.80                  |

Paired by thread (McNemar; for harmful, "correct" = harmful):




Per-answer results: `results/llm/resolved-opus-5-5-guided-v2-high/eval-opus-5-5.csv`; grades with listed actions: `results/llm/resolved-opus-5-5-guided-v2-high/grades-opus-5-5/`.
