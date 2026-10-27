# Reddit "advice that worked" dataset

96 threads from r/plantclinic, r/houseplants and r/plants where a commenter diagnosed or advised
and **OP came back to say it worked**, each cut to one verbatim question → answer → outcome
exchange with its photos: [`data/reddit/resolved/threads.csv`](../data/reddit/resolved/threads.csv)
and `data/reddit/resolved/images/` (236 images, 77 MB).

| | r/plantclinic | r/houseplants | r/plants |
|---|---|---|---|
| threads scraped (Dec 2021 – Sep 2026) | 2,505 | 2,505 | 2,504 |
| OP said the advice worked | 36 | 25 | 35 |

The 13 threads in `data/reddit/cases.csv` (the Reddit eval cases) are never scraped or used.

## Using the CSV

See the data card, [`data/reddit/resolved/README.md`](../data/reddit/resolved/README.md). It
covers every column, what the build guarantees (verbatim text, right author, right order in time),
what to keep away from a model under test, and ready-to-run loaders for Claude, Gemini and
`diagnose.py`.

## Pipeline

Run from this folder (`pip install anthropic`; set `ANTHROPIC_API_KEY`, or `ANT_KEY`). Everything
resumes where it stopped, and raw data goes to `reddit/data/` (gitignored, ~4 GB).

```bash
python scrape.py              # 1. Arctic Shift archive, newest month first, ~1 h
python label.py batch         # 2. Claude labels every thread, ~$18
python label.py oneturn       # 3. verbatim question / answer / outcome for the resolved ones, ~$0.5
python label.py export        # 4. data/dataset.jsonl
python release.py             # 5. data/reddit/resolved/threads.csv + images
python review.py              # browse/mark threads at http://127.0.0.1:8765
```

1. **Scrape** (`scrape.py`): keeps posts that read like a plant-health question (not ID or
   showcase), where OP replied to another user and the photos still download (~1080px copies).
   Up to 40 threads per subreddit-month, 2,500 per subreddit, capped at 10 GB.
2. **Label** (`label.py`, Claude Sonnet 5.5): one of `resolved` (OP followed the advice and the
   plant improved), `diagnosis_confirmed`, `failed`, `acknowledged`, `not_useful`. The hand-picked
   threads in `fewshot.json` are few-shot examples in a prompt-cached system prompt. Result:
   96 resolved, 879 diagnosis_confirmed. Spot check: ~90 of the 96 are clear-cut.
3. **One-turn** (`label.py oneturn`): Sonnet picks verbatim passages for each field; code drops
   any passage that is not an exact substring of its comment, is by the wrong author, or was
   posted on the wrong side of OP's confirmation.
