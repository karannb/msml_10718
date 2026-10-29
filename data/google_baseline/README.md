# Frozen Google Search baseline

96 resolved Reddit threads, two paraphrases per thread (192 searches), five retained
source positions per query (960 positions; 814 distinct source URLs). These are
traditional Google results collected October 28–29, 2026. Google AI summaries were
not used as answers. Query writing, extraction and grading were assistant-assisted;
this is a Google retrieval baseline, not a claim of wholly non-ML processing.

## What is saved

- `2026-10-29/frozen-queries.jsonl`: the exact title and symptoms/context paraphrases,
  input provenance and freeze timestamps. Queries were fixed before retrieval.
- `2026-10-29/evidence/`: original search/page snapshots, source text, video
  descriptions/transcripts, retry captures and reference clarifications. These are
  raw captures, not cleaned or synthesized answers. Search snapshots can contain
  Google UI/AI text; **the grading runner does not use search snapshots as answers**.
- `2026-10-29/source-packets.jsonl`: query-to-source mapping and the exact captured
  files for each source. Content is stored once in `evidence/`, not duplicated here.
- `2026-10-29/selections/`: all 192 frozen source-answer passages, their URLs,
  selection reasons, original line ranges, hashes and timestamps. These contain
  the text Claude can grade directly, including warnings and conflicting advice.
- `2026-10-29/query_inputs.jsonl` and `references.jsonl`: question-only inputs and
  original dataset reference fields, kept separate. Dataset images remain in
  `data/reddit/resolved/images/`; the API judge uses `[photo]` placeholders, matching
  the repository's existing advice-judge workflow.
- `2026-10-29/reference-audit.jsonl`: reference-only corrections/ambiguities, without
  source grades. Optional for Claude; never silently merged into the original data.
- Protocols, original exclusions, commit/dataset provenance and `checksums.json`.

Some sources were inaccessible or lacked usable transcripts. Capturing a page is
not proof of reading its unavailable content. Such evidence remains unresolved.
Two original-owner cross-posts discovered in review (zero-based query 17/rank 1,
142/rank 2) are flagged in the source packets and excluded from independent
retrieval. No post-hoc lower-ranked replacement was introduced. The frozen selected
answer for query 17 is still saved and flagged as contaminated.

## Assistant evaluations

[`results/google-baseline/assistant-v1/`](../../results/google-baseline/assistant-v1/)
contains all 192 evaluations, five source judgments per query, rubric reasons,
action/time/cost estimates, summary statistics, the original grades before audit,
and the adjudication log. Open `REPORT.html` for the complete readable report.
The grader is `assistant_in_conversation`, not Claude. These results are never a
Claude cache or included in Claude prompts.

Independent-source verified hits: title 76/96 (79.2%), context 80/96 (83.3%).
Unresolved: 9 and 10, respectively; those percentages are lower bounds. Safe & useful
first answers: 1/96 and 6/96. Solved within capacity: 0/96 and 4/96.

The assistant used active owner time for the final capacity audit, preserving
elapsed-time estimates as a sensitivity. References sometimes show recovery without
specifying every performed action. Scope of frozen answer selections varies from
focused sections to broad guides; this affects task counts. All limitations and
post-hoc decisions are documented in the report. An auxiliary explanation-coverage
metric was not scored. The structural validation file is not independent semantic
validation or proof of blinding.

## Regrade with a Claude API key

Run from the repository root. Existing `score_resolved.py`, `judge_resolved.py`,
their prompts and their model results are unchanged.

```sh
python eval_google.py validate
python -m unittest discover -s tests -p 'test_eval_google.py'
python eval_google.py export-prompts --start 0 --end 1 --output /tmp/google-prompt-preview
```

The three commands above are offline and require only Python's standard library.
Install the repository requirements for API grading. Set `ANTHROPIC_API_KEY` in your
environment or the ignored repository `.env`; never commit it. Select a model ID
available to your account, e.g. assign it to `CLAUDE_GRADER_MODEL`, then run:

```sh
python eval_google.py grade --model "$CLAUDE_GRADER_MODEL" --run claude-dataset-v1 --start 0 --end 1
python eval_google.py grade --model "$CLAUDE_GRADER_MODEL" --run claude-dataset-v1 --start 0 --end 192
python eval_google.py report --run claude-dataset-v1
```

The first command is a small paid smoke run; the second resumes matching calls and
finishes the dataset. This preparation did **not** make any paid API calls.
Results go only to `results/google-baseline/claude/<run>/`. Each response records
model, token usage, input hash, timestamp and verdict. Writes are atomic. A change
to the model, prompts, input or reference mode requires a new run name; a stale cache
cannot silently pass as current. No credentials are written to results.

Default `--reference-mode dataset` uses original reference fields, for continuity
with the existing repository judge. Optional `--reference-mode audited` appends the
reference-only audit, which clarifies actual OP actions and ambiguous outcomes.
Use a **different run name** for that condition. This audit was authored by the same
assistant, so it is not an independent reference review.

`--tasks resolved quality` grades the frozen selected answer with the two existing
rubrics (384 calls for 192 queries). Add `retrieval`, or use the default task list,
to grade each independent source separately (958 more calls; 1,342 total). Source
jobs use actual page/transcript text and require valid evidence spans for hits;
search snippets and assistant hit labels are not inputs. This allows independent
Claude scores on exactly the saved retrieval, without performing new searches.
These can be substantial prompts; preview/smoke-test before running all jobs.
The API runner follows the API request format already used by this branch. Live
model availability and a real authenticated response have not been tested here.

Unfinished queries have null aggregate metrics. Completed API outputs are labeled
`graded_pending_review` / `not_independently_reviewed`; review hit evidence and harm
judgments before treating them as final. The runner validates schema, score ranges,
action estimates and cited line ranges, but cannot automatically establish that a
quoted passage semantically supports a judgment. Raw JSON remains inspectable.

Assistant scores and future Claude scores are separate experimental conditions.
The Claude path retains the exact repository rubric wording; it does not silently
apply the assistant's active-time amendment. Reference mode, grader and these
methodological differences must be disclosed in any comparison.
