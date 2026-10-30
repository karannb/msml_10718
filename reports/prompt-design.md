# Prompt design for Haiku 5.5 on the resolved Reddit threads

**Question.** Can the system prompt (extra plant-care knowledge, answer-format rules, reasoning instructions) or web
search make Claude Haiku 5.5's answers to Reddit plant-help posts match the fix that worked more often?

**Answer: no measurable gain.** No prompt element and no web search beat the `guided-v2` prompt. On the 32 development
threads the differences are all within ±0.03 of its advice score. On the 64 held-out test threads, search changes the advice
score by −0.016 [−0.070, +0.035].

## Setup

- **Model under test:** `claude-haiku-5-5` (medium effort). It sees only the post: its photos, title and text. No
  classifier output.
- **Grader:** `claude-sonnet-5-5`. It compares each answer with the thread's confirmed problem, the advice that worked
  and the poster's outcome, using the grader prompt in `eval_resolved.py`.
  - Diagnosis score: 1 if correct, 0.5 if partial, 0 if wrong.
  - Advice score: 1 if following the answer's main advice would most likely have produced the same fix, 0.5 if
    partial, 0 if not.
  - Harmful: true if the advice would likely make this plant worse.
- **Threads:** `data/reddit/resolved/threads.csv`, split with seed 0 in `eval_resolved.py`.
  - 32 development threads, used for every design decision.
  - 64 test threads, used once, after the design was finished.
- **Repeated answers:** each thread is answered several times (`--samples`). Scores are averaged per thread, then over
  threads. Brackets are 95% bootstrap intervals over threads of the paired difference with `guided-v2`.
- **Starting prompt `guided-v2`** (`diagnose.py`, `SYSTEM_PROMPTS`):
  - a checklist for telling causes apart (watering, light, pests, other causes, "it may be normal", weighing the
    poster's details);
  - one main cause first, then 2–4 fix steps, in about 250 words.
- **Web search** (`--search`): Anthropic's server-side `web_search` tool, at most 3 searches per answer, with a system
  note asking the model to check its diagnosis against reliable sources.
  - Blocked domains: reddit.com, redd.it and the other Reddit hosts, Reddit mirror and archive sites, archive.org and
    archive.ph (`diagnose.BLOCKED_DOMAINS`).
  - Every query and result URL is saved with the answer.
  - Results from a blocked domain, or with a title close to the post's, are flagged under `possible_leaks`. All flagged
    results were checked by hand: they are generic care guides (for example "Calathea Care Guide"), not the threads.

## Prompt elements

Each element is added to `guided-v2` alone (`--prompt guided-v2+<element>`; see `diagnose.ELEMENTS`). The knowledge was
written from general houseplant-care knowledge, without reading the evaluation threads.

| Element | What it adds or changes |
|---|---|
| plant-care notes (`kb`) | care needs of common plant groups, a table from symptoms to usual causes, standard fixes |
| common causes ranked (`priors`) | how often each kind of cause is the real one on help forums; prefer common causes |
| answer the asked question (`question`) | answer the poster's actual question (growth, repotting, ...) even if nothing is wrong |
| weigh 3 causes first (`differential`) | think through 3 candidate causes against the evidence before answering |
| short fixed format (`format`) | fixed headings, one action first, at most 3 more, at most 180 words |
| fix stated first (`lead`) | first sentence says what to do |
| at most 150 words (`short`) | word limit 250 → 150 |
| without item k (`drop2`, `drop4` to `drop7`) | removes one item of `guided-v2`'s checklist |

## Results on the 32 development threads

**Round 1 and round 2: 2 answers per thread (64 answers per row).**

| Prompt | Search | Advice score | Diagnosis score | Harmful |
|---|---|---:|---:|---:|
| `guided-v2` | no | 0.758 | 0.703 | 0.062 |
| `guided-v2` | yes | 0.719 | 0.664 | 0.078 |
| + plant-care notes | no / yes | 0.719 / 0.695 | 0.680 / 0.688 | 0.062 / 0.109 |
| + common causes ranked | no / yes | 0.719 / 0.680 | 0.664 / 0.703 | 0.062 / 0.078 |
| + answer the asked question | no / yes | 0.695 / 0.703 | 0.648 / 0.703 | 0.078 / 0.062 |
| + weigh 3 causes first | no / yes | 0.703 / 0.680 | 0.672 / 0.703 | 0.047 / 0.094 |
| + short fixed format | no / yes | 0.680 / 0.672 | 0.680 / 0.688 | 0.125 / 0.109 |
| + fix stated first | no | 0.680 | 0.656 | 0.078 |
| + at most 150 words | no | 0.711 | 0.633 | 0.078 |
| without the watering item | no | 0.688 | 0.664 | 0.062 |
| without the pests item | no | 0.734 | 0.695 | 0.078 |
| without the other-causes item | no | 0.695 | 0.664 | 0.109 |
| without the may-be-normal item | no | 0.719 | 0.664 | 0.047 |
| without the weigh-poster-details item | no | 0.703 | 0.680 | 0.078 |
| `guided-v2`, search only if unsure | no searches made | 0.703 | 0.695 | 0.062 |
| no system prompt (`plain`) | no | 0.680 | 0.641 | 0.062 |

Every row is below the first `guided-v2` row, but that row is misleading:

- **Its first answer per thread is the very answer set `guided-v2` was chosen on**, back when it was written. Those
  answers score 0.781 on advice; its fresh second answers score 0.734.
- **The "search only if unsure" run shows the noise level.** The model never searched, so its answers differ from
  `guided-v2`'s only by an ignored paragraph. Yet it scores 0.055 lower. So at 2 answers per thread, differences of
  about 0.05 are noise.

**Round 3: the closest contenders, 6 answers per thread.** `guided-v2` here uses only its 5 fresh answers per thread.

| Prompt | Answers | Advice score | Advice change vs `guided-v2` | Diagnosis change vs `guided-v2` |
|---|---:|---:|---|---|
| `guided-v2` | 160 | 0.716 | | |
| + plant-care notes | 192 | 0.727 | +0.011 [−0.023, +0.047] | +0.002 [−0.024, +0.027] |
| without the pests item | 192 | 0.716 | +0.001 [−0.026, +0.026] | +0.007 [−0.019, +0.033] |
| + common causes ranked | 192 | 0.708 | −0.007 [−0.035, +0.019] | +0.005 [−0.020, +0.028] |
| `guided-v2` with web search (4 answers) | 128 | 0.719 | about +0.003 | |
| no system prompt (2 answers) | 64 | 0.680 | −0.036 [−0.084, +0.014] | −0.034 [−0.084, +0.022] |

## Held-out check on the 64 test threads (2 answers each)

| Prompt | Advice score | Diagnosis score | Harmful | Searches per answer |
|---|---:|---:|---:|---:|
| `guided-v2`, no search | 0.621 | 0.680 | 0.117 | 0 |
| no system prompt (`plain`) | 0.609 | 0.629 | 0.133 | 0 |
| `guided-v2` with web search | 0.605 | 0.684 | 0.172 | 1.7 |

Paired differences:

| Comparison | Advice | Diagnosis | Harmful |
|---|---|---|---|
| `guided-v2` minus no system prompt | +0.012 [−0.031, +0.055] | +0.051 [+0.000, +0.102] | −0.016 [−0.062, +0.031] |
| `guided-v2` with search minus without | −0.016 [−0.070, +0.035] | +0.004 [−0.039, +0.047] | +0.055 [−0.016, +0.133] |

### Adding the classifier's output on the test threads (2 answers each)

Option `llm+classifier` adds the DINOv2 classifier's probabilities for each photo, with its 5 classes and a warning that it
is often wrong.

| Setting | Advice score | Diagnosis score | Harmful |
|---|---:|---:|---:|
| `guided-v2`, no search, post only | 0.621 | 0.680 | 0.117 |
| `guided-v2`, no search, + classifier | 0.605 | 0.664 | 0.133 |
| `guided-v2` with search, post only | 0.605 | 0.684 | 0.172 |
| `guided-v2` with search, + classifier | 0.637 | 0.691 | 0.141 |

Paired differences, with the classifier minus post only:

| Setting | Advice | Diagnosis | Harmful |
|---|---|---|---|
| No search | −0.016 [−0.059, +0.027] | −0.016 [−0.055, +0.020] | +0.016 [−0.031, +0.062] |
| With search | +0.031 [−0.016, +0.082] | +0.008 [−0.031, +0.051] | −0.031 [−0.102, +0.039] |

There is no clear effect in either setting.

### What the searches did (test threads, 128 answers)

**How much it searched:** every answer searched, 1 time in 69 answers and 2 times in 189.

**Where results came from** (4,257 result pages):

| Source | Share of result pages |
|---|---:|
| Gardening blogs and magazines | 73% |
| Plant-care apps | 12% |
| Plant shops and growers | 10% |
| Universities, extension services, botanic gardens | 3% |

**What the searches were about:** a Haiku pass labelled each answer's queries against the thread's confirmed problem.
- 86% of answers ran at least one search about the confirmed problem.
- 68% searched mainly the cause the answer then gave.
- Answers whose searches missed the confirmed problem scored 0.25 on advice, against 0.66 for the others.

**Search confirms rather than corrects.** Haiku forms its guess from the photo, then searches for that guess.
- 1h8hroj: it searched "basil wilting root rot overwatering signs" for a basil that needed water.
- 1o3aiun: it searched "rosemary root rot overwatering symptoms" for a rosemary drying out in terracotta.
- 1e73qwo: it searched "spider plant direct sun scorch" for a plant that needed more light.

The search results back up the wrong reading of the photo, so search can't fix a misread photo, which is the main
failure.

### Opus 5.5 at high effort, with and without web research

This runs on the first 32 test threads in split order, with 1 answer per thread.

The research instruction (`--search research`):
- allows up to 5 searches;
- tells the model to identify the plant first, then look up its needs, every cause that could fit, and how each one is
  cured.

Opus uses the `web_search_20260209` version of the tool, which filters results with code; Reddit is blocked as before.
Haiku rows are the means of 2 answers on the same 32 threads.

| Setting | Advice score | Diagnosis score | Harmful |
|---|---:|---:|---:|
| Haiku, medium effort, no search | 0.688 | 0.711 | 0.062 |
| Haiku, medium effort, search | 0.656 | 0.703 | 0.078 |
| Opus, high effort, no search | **0.750** | **0.750** | 0.062 |
| Opus, high effort, research search (4.8 searches per answer) | 0.703 | **0.750** | 0.062 |

Paired differences:

| Comparison | Advice | Diagnosis |
|---|---|---|
| Opus research search minus Opus without search | −0.047 [−0.109, 0.000] | 0.000 |
| Opus without search minus Haiku without search | +0.062 [−0.023, +0.156] | +0.039 [−0.039, +0.117] |

- **Search rarely changes Opus's grade.** It changes the advice grade on only 3 of the 32 threads, and all 3 get worse.
  In those threads the extra research pulls in another cause (dry air, root rot) or restructures the answer away from
  the plain fix.
- **Search costs a lot more:** about $0.39 per Opus answer with research, against $0.05 without.
- **The one flagged result is generic:** a care guide, "Why Is My Croton Wilting After Repotting It?".

### Full evaluation: Opus 5.5 at max effort, `guided-v2`, no search, all 96 threads

This is the best setting found above, with effort raised to max. It gives 1 answer per thread, graded by Sonnet.

- **Output limit:** 64,000 tokens. At 16,000, max-effort thinking used the whole budget and 3 of 4 trial answers came
  back empty.
- **Answer length:** about 23,800 output tokens on average.
- **Cost:** about $48 for the run.

Haiku rows are on the same 96 threads, averaged over their answers. For `guided-v2` on the dev threads, only the fresh
answers count.

| Setting | Advice score | Diagnosis score | Harmful |
|---|---:|---:|---:|
| Haiku, no system prompt | 0.633 | 0.633 | 0.109 |
| Haiku, `guided-v2` | 0.653 | 0.678 | 0.101 |
| Opus, max effort, `guided-v2` | **0.755** | **0.740** | **0.021** |

Paired differences, Opus at max effort minus each Haiku setting:

| Compared with | Advice | Diagnosis | Harmful |
|---|---|---|---|
| Haiku `guided-v2` | +0.103 [+0.045, +0.160] | +0.061 [+0.008, +0.118] | −0.080 [−0.140, −0.027] |
| Haiku, no system prompt | +0.122 [+0.065, +0.180] | +0.107 [+0.049, +0.167] | −0.089 [−0.151, −0.031] |

- **The model is the lever that works.** Opus at max effort matches the fix that worked clearly more often than Haiku,
  and gives about a fifth as many harmful answers (2 in 96).
- **Max effort is no better than high effort.** On the 32 test threads where both exist (1 answer each), max scores
  0.656 on advice and high scores 0.750: −0.094 [−0.188, 0.000]. High effort costs about $0.05 per answer, against
  $0.47 for max.

### Telling the model the evaluation's limits (all 96 threads, 1 answer each)

The `evals` branch scores answers with Opus 5.5 (`score_resolved.py`, `prompts/resolved_grader.txt`). An answer counts
as **Solved** when three things hold:
- its main advice would most likely have produced the confirmed fix;
- it is not harmful;
- it has at most 4 actions, each under 15 minutes a day and at most $15.

The grader counts every check, conditional step and alternative as an action. Every system scored 0% Solved, because
its answers had 8–10 actions. None of the prompts above told the model about these limits.

Element `limits` (`diagnose.ELEMENTS`) replaces the "How to answer" part of `guided-v2` with the evaluation's rules:
- at most 4 numbered actions, where checks, "if … then" steps and alternatives each count, and no advice outside the
  list;
- each action under 15 min/day and at most $15, naming the product, the amount and the time;
- say so when the plant is healthy or the change is normal, and recommend no treatment;
- repotting, root trimming or pesticides only when clearly needed;
- never change the watering without checking the soil first, and never reassure the owner about pests or rot.

Haiku 5.5, post only, graded by Opus 5.5:

| Measure | `guided-v2` | `guided-v2+limits` |
|---|---:|---:|
| Actions per answer (lower is better) | 8.6 | 6.6 |
| Answers within the action limit (higher is better) | 1% | 7% |
| Solved (higher is better) | 0/96 | 2/96 |
| Solved without the action limit (higher is better) | 45% | 46% |
| Diagnosis correct (higher is better) | 56% | 53% |
| Potential harm (lower is better) | 12% | 16% |
| False alarms on the 5 healthy threads (lower is better) | 2 | 2 |

The changes are within noise: the diagnosis is correct or partly correct in 83% and 79% of answers (McNemar p = 0.29), and the harm p is 0.51. The Sonnet grader agrees: the advice
score is 0.651 with the limits and 0.653 without. Answers are shorter but still go over the limit, for three reasons:
- **Haiku follows the rule only in part.** After its 4 steps it often adds a line like "if the stems turn soft, repot
  and trim the roots", which the grader counts as a fifth action of 30 minutes.
- **The grader splits steps.** It counts "check the soil, then water" as 2 actions and "watch for new growth" as 1.
- **Repotting and root work take 15 minutes or more.** 65 of the 96 answers still have such an action, and for
  root rot it is often the fix that worked.

Reports: `reports/eval-resolved-haiku-5-5-guided-v2.md` and `reports/eval-resolved-haiku-5-5-guided-v2+limits.md`.

**The same comparison with Opus 5.5** at high effort, no search: the best Opus setting above. Opus follows the limits
more closely than Haiku, and it gets less right as a result. Graded by Opus 5.5:

| Measure | `guided-v2` | `guided-v2+limits` | McNemar p |
|---|---:|---:|---:|
| Actions per answer (lower is better) | 8.4 | 5.1 | |
| Answers within the action limit (higher is better) | 0% | 23% | |
| Solved (higher is better) | 0/96 | 7/96 | 0.016 |
| Solved without the action limit (higher is better) | 60% | 43% | |
| Diagnosis correct or partly correct (higher is better) | 92% | 79% | 0.002 |
| Potential harm (lower is better) | 8% | 16% | 0.039 |
| False alarms on the 5 healthy threads (lower is better) | 0 | 1 | |

The Sonnet grader agrees. Limits minus no limits, paired by thread:
- advice: −0.130 [−0.188, −0.078], from 0.755 to 0.625;
- diagnosis: −0.073 [−0.130, −0.016];
- harmful: +0.083 [+0.021, +0.156].

The Solved gain is real, but small. To fit 4 short actions, Opus drops the checks and backup steps that were catching
the actual cause, so it misses the fix more often and gives more harmful advice. The "at most 4 short actions" rule
pulls against the correctness and harm criteria. Solved rewards answers that fit the rule, not answers more likely to
fix the plant.

Reports: `reports/eval-resolved-opus-5-5-guided-v2-high.md` and `reports/eval-resolved-opus-5-5-guided-v2+limits-high.md`.
Opus answers cost $0.047 each at high effort.

## Conclusions

- **Prompt additions don't help Haiku here.** Knowledge notes, cause rankings, format rules and reasoning instructions
  are all within ±0.03 of `guided-v2` on advice. Neither do removals.
- **Web search doesn't help.** Haiku searches for the symptoms and finds sensible pages, such as university extension
  services. Its answers match the fix no more often, and on the test threads somewhat more of them are graded harmful
  (not significant).
- **`guided-v2` helps the diagnosis only:** +0.05 on the test threads over no system prompt, with no clear gain on advice.
- **Development scores overstate test scores.** Advice is about 0.72 on the dev threads and 0.62 on the test threads for
  the same prompt, so the dev threads are easier or the earlier prompt work fits them. This is why the test threads were
  kept for one final check.
- **Writing the evaluation's limits into the prompt raises Solved only a little, and costs quality.** Solved goes from
  0 to 2 of 96 answers with Haiku and from 0 to 7 with Opus. But Opus then finds the right cause less often (92% →
  79%) and gives more harmful advice (8% → 16%). The capacity rule, as graded, works against the other criteria.
- **Next levers are outside the prompt:** a stronger answering model (Sonnet scored higher than Haiku in the Opus
  grading on the `evals` branch), or several answers combined into one.

## Cost and reproduction

About $107 of API credits ($23 for the prompt rounds, $4 for the classifier runs, $13 for the Opus high-effort runs, $48 for the Opus max-effort full evaluation, $17 for the evaluation-limits runs and their Opus grading):

| Item | Cost each |
|---|---:|
| Haiku answer, no search | $0.001 |
| Haiku answer, with search | $0.023 |
| Sonnet grade | $0.004 |

`jobs/run_many.py` runs several configurations in one process; the login node allows few threads per user, and the
organization caps how many API requests can run at once. `jobs/compare_prompts.py [dev|test]` prints the tables above
and the running spend.

```bash
python jobs/run_many.py "--prompt guided-v2+kb --threads dev --options llm --samples 6 --grader claude-sonnet-5-5 --workers 3"
python jobs/compare_prompts.py dev
```

Experiments are recorded on the lab site, subproject `prompt-design`.
