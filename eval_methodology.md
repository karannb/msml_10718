# Evaluation methodology

## Goal

The app works if plants cared for with its advice end up healthier than comparable plants cared for without it (Google search, a rule of thumb, or a general LLM), with domain experts judging outcomes and advice. Until that is measured, we evaluate classification and recommendation separately.

**Capacity:** a recommendation has at most 4 short actions. A short action takes under 15 minutes and costs at most $15.

## Evaluation sets

| Set | Cases | Use |
|---|---|---|
| Classification | 100 Indoor images (`data/testset.csv`, seed 10718, test + valid folders, no augmented copies, 6–7 per class across 16 classes) | tests the range of conditions, not how often they occur; excluded from training and tuning |
| Recommendation | Reddit posts from r/plants, r/houseplants and r/plantclinic (`data/reddit_cases.csv`) | 8 usable cases as of 27 Oct 2026; the set grows |

Adding a Reddit case:

- **Inputs:** the first photo, plus the poster's title and body only, never replies.
- **Reference:** usable only when the thread settles the cause (poster confirmation, a reported fix, or a recognizable feature). Advice alone is `unconfirmed`, and unconfirmed cases are not scored.
- **Healthy plants:** include them, so false alarms can be measured.
- **Contamination:** check a reverse image search first, and record the post date.
- **Exclusion:** evaluation threads are never used for training or few-shot examples.

## Metrics

**Classification** (one prediction per image): accuracy and balanced accuracy, with 95% bootstrap CIs. Always guessing the most common broad category scores 39%.

**Recommendation**, per system and input condition (image + generic question, or + poster details):

| Metric | Definition |
|---|---|
| Reference coverage | the reference explanation appears in the answer (or the first five eligible Google results), even among several causes |
| Solved | appropriate care, no potential-harm flag, and at most 4 short actions; unclear time or cost means not solved |
| Potential harm | advice or reassurance that could worsen the condition, allowing for safeguards such as checking the soil before watering |

Rates are reported with 95% Wilson CIs. Coverage is also reported without the cases where a search tool retrieved the original post.

**Short actions:** every task the user must do counts, including checks and conditional steps. A repeated task counts once, timed per day, so "water every hour" is not short. Basic household supplies are free (water, scissors, dish soap, rubbing alcohol, cotton swabs, plastic bags). Record one row per action (time, cost, unclear yes/no) to compute Solved.

**Endpoint systems** (`evaluate.py`): rule-based harm flags, citation checks, the LLM judge's safe & useful rate (harmfulness, specificity and feasibility all at least 4 of 5), error rate, p95 latency, cost per 1,000 requests, and expected error cost. The error-cost weights are placeholders. Systems are compared with McNemar's test.

## Baselines

| | Baseline | Setup |
|---|---|---|
| A | Google text search (non-ML) | each post's exact title; first five organic results, excluding the original post, copies, ads and AI Overviews; 5 Oct 2026 |
| B | Claude Sonnet 5.5, Medium effort | fresh claude.ai chat per case and condition; no replies, references or examples |
| — | Google Lens / AI Overview | same two conditions; supplementary, because it can retrieve the source post |
| C | gemini-3.1-flash-lite, temperature 0 | zero-shot classification on the 100 images. Prompt 1: 5 broad categories. Prompt 2: the 16 native classes |

## Results (27 Oct 2026)

**Reference coverage** (8 Reddit cases):

| Baseline | Coverage |
|---|---|
| Google text search | 4/8 (50%) |
| Claude: generic question | 7/8 (88%) |
| Claude: poster details | 8/8 (100%) |
| Lens: generic question* | 5/8 (62%) |
| Lens: poster details* | 8/8 (100%) |

\*Lens retrieved the original post in 2 of 8 generic and 5 of 8 poster-details cases.

**Claude advice:** Solved 2/8 under both conditions. Potential harm 2/8 with the generic question (thrips reassurance) and 1/8 with poster details (oil and sulfur together).

**Classification:**

| Setup | Accuracy | Balanced accuracy |
|---|---|---|
| Prompt 1: 5 broad categories | 62% | 54% |
| Prompt 2: 16 native classes | 61% | 62% |

In Prompt 2, the plant was identified correctly in 81% of images and healthy vs. unhealthy in 93%.

**The 96 resolved Reddit threads** (answers from `eval_resolved.py`; graded by Opus 5.5 with `prompts/resolved_grader.txt`, which covers every metric above; `score_resolved.py`). Baseline B is run here through the API with `diagnose.py`'s prompt at medium effort, not in claude.ai. Baseline A (Google) is the one frozen source passage selected per search (`data/google_baseline/`), searched by the post's title or by its symptoms and context, graded by the same prompt (`eval_google.py`, run `opus-5-5-v1`).

| Metric | Google: title (A) | Google: context (A) | Sonnet 5.5 (baseline B) | Sonnet + classifier | Haiku 5.5 | Haiku + classifier |
|---|---|---|---|---|---|---|
| Reference coverage | 47% (37–57%) | 60% (50–70%) | 94% (87–97%) | 88% (79–93%) | 84% (76–90%) | 80% (71–87%) |
| Diagnosis correct | 9% (5–17%) | 18% (11–27%) | 54% (44–64%) | 47% (37–57%) | 42% (32–52%) | 50% (40–60%) |
| Solved | 0% (0–4%) | 3% (1–9%) | 0% (0–4%) | 0% (0–4%) | 0% (0–4%) | 0% (0–4%) |
| Solved without the capacity rule | 8% (4–16%) | 17% (11–25%) | 48% (38–58%) | 46% (36–56%) | 38% (28–47%) | 45% (35–55%) |
| Potential harm | 34% (26–44%) | 23% (16–32%) | 10% (6–18%) | 15% (9–23%) | 20% (13–29%) | 10% (6–18%) |
| False alarm (5 healthy threads) | 1/5 | 3/5 | 1/5 | 1/5 | 2/5 | 1/5 |
| Actions per answer | 7.6 | 6.4 | 10.0 | 9.5 | 9.1 | 8.6 |
| USD per 1,000 answers | — | — | 17.88 | 18.76 | 1.16 | 1.28 |

Paired by thread (McNemar), baseline B beats Google on coverage (48 vs 3 discordant threads by title, 34 vs 2 by context; p < 1e-7) and harm (3 vs 26, p < 1e-4; 8 vs 20, p = 0.036). The Google passage is graded alone; coverage across all five results, as in the report's definition, is not graded by Opus (the assistant's grades in `results/google-baseline/assistant-v1/` give 79% and 83%).

Haiku + classifier vs baseline B:
- **Coverage:** lower. The baseline covers 13 threads that Haiku + classifier misses, and the reverse never happens (p = 0.0002).
- **Harm:** equal, 4 vs 4 discordant threads (p = 1).
- **Cost:** about 14 times cheaper.

The classifier halves Haiku's potential harm (p = 0.035) but doesn't help Sonnet: coverage is 1 vs 7 discordant threads (p = 0.07) and harm 4 vs 0 (p = 0.125). With three tests per comparison, none of these p-values survives correction except the coverage gap against baseline B.

The 1–5 advice judge (`judge_resolved.py`; table in the README) agrees on harm (23 of 24 severe-harm answers are graded harmful) and diagnosis (92%), but its feasibility score ignores capacity: 375 of 379 over-capacity answers score 4 or 5.

The capacity rule decides Solved for every system: at most 3% of LLM answers have 4 or fewer actions. Opus agrees with the original Haiku grades on 77–85% of diagnoses, 77–79% of advice grades and 86–93% of harm grades. The rule-based harm flags overlap little with the grader's harm judgments (4 of 28 flagged Haiku answers), so they don't replace the judge.

## Limits

- **Size:** with 8 cases, a rate is known to about ±28 points. Ranking systems needs about 100 cases (±10); bounding false alarms below 16% needs at least 20 healthy cases.
- **References:** taken from Reddit threads, not verified by experts.
- **Not yet measured:** plant recovery, expert agreement, and calibration.
- **Not in the repo yet:** the Gemini prompts and predictions (Prompt 1 and 2 reports), action-level time and cost records, and the Reddit photos and post text needed to run endpoint systems on Reddit cases.

## Deployment criterion

A classifier + LLM pipeline must beat the same LLM alone on a larger held-out set: solve more cases without more harm, or less harm without solving fewer cases. Advice must stay within capacity, and plant specialists review results before deployment.
