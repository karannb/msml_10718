# Remedy corpus

`data/corpus_sources.csv` indexes 108 university extension pages on houseplant problems, for grounding and checking advice citations. It stores URLs and tags only; the page text is copyrighted and stays out of git.

| Column | Meaning |
|---|---|
| `labels` | labels covered: healthy / watering / fungal_bacterial / pest / other |
| `plants`, `problems` | plants and problems named on the page |
| `use` | `corpus` (99 pages); `holdout_gold` (8): cited by `gold_advice.json`, so kept out of retrieval; `duplicate` (1) |
| `fetch` | `curl` loads with a plain request; `browser`: Clemson HGIC returns 403 to scripts |

Pages per label: pest 63, other 55, watering 53, healthy 48, fungal_bacterial 29. Publishers: UMD, Clemson HGIC, NC State, UC IPM, Minnesota, Iowa State, Penn State, Illinois, UF/IFAS, Colorado State, Missouri; URLs checked 25 Oct 2026.

Caveats: the tags were assigned by an LLM and haven't been checked by hand, and no page mentions cochineal.
