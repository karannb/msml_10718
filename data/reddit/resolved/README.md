# Reddit "advice that worked" threads: data card

`threads.csv` has **96 rows, one per Reddit thread**, where someone asked for help with a sick
plant, another user diagnosed or advised, and the poster (OP) later said the advice worked.
Each thread is cut to one exchange, copied verbatim from Reddit:

- **question**: what OP asked, with their photos
- **answer**: what other users told them
- **outcome**: OP saying it worked, sometimes with an "after" photo

`images/` holds the 236 photos. How the data was built: [`reddit/README.md`](../../../reddit/README.md).

| | |
|---|---|
| Subreddits | r/plantclinic 36, r/plants 35, r/houseplants 25 |
| Posted | 2022-01-13 to 2026-09-10 |
| Photos per thread | 1 to 7 (1: 30 threads, 2: 29, 3: 18, 4+: 19) |
| Photos | 236 files (231 .jpg, 5 .png). 212 post photos as Reddit's ~1080 px copies; 24 photos OP posted in comments are originals, up to 4096 px and 4.5 MB |
| Question length | median 386 characters (max 928). 58 include details OP added in comments; 7 are only a title and photos |
| Answer length | median 202 characters (max 1176). 35 combine more than one comment |
| Outcome length | median 105 characters (max 737). 22 end with an "after" photo |

## Columns

Read the file with `csv` or pandas: fields contain line breaks inside quotes, so line-based tools
(`wc -l`, `head`, `cut`) give wrong answers. The file is UTF-8 and every value is a string.

| Column | What it holds |
|---|---|
| `thread_id` | Reddit post ID, e.g. `16w508b` |
| `subreddit` | `plantclinic`, `houseplants` or `plants` |
| `created` | date of the post, UTC, `YYYY-MM-DD` |
| `url` | the thread, `https://www.reddit.com/r/<sub>/comments/<id>/`. Add `comment/<comment_id>/` for one comment |
| `question` | `{title}\n\n{Image_01} {Image_02} …\n\n{OP's passages}`, explained below |
| `answer` | passages from other users' comments, joined by blank lines, oldest first |
| `outcome` | passages from OP's confirming comment, then `\n\n{Image_NN}` if OP posted an "after" photo there |
| `plant` | plant name, or `unknown`. **Written by Claude from the whole thread** |
| `problem` | the confirmed diagnosis in a few words, e.g. `thrips infestation`. **Written by Claude from the whole thread** |
| `advice_summary` | the advice as a `;`-separated list. **Written by Claude from the whole thread** |
| `community_agrees` | `True` if Claude judged that at least two commenters gave the same diagnosis (47 rows), else `False` |
| `n_images` | number of filled `Image_NN` columns |
| `question_sources`, `answer_sources`, `outcome_sources` | `;`-separated IDs of the comments each field was copied from, oldest first. `post` means the post body |
| `advice_comment_url` | link to the comment Claude picked as the main advice |
| `outcome_comment_url` | link to OP's confirming comment |
| `Image_01` … `Image_07` | path to a photo, relative to the repo root, e.g. `data/reddit/resolved/images/16w508b_01.jpg`. Empty when a thread has fewer photos |

### How `question` is put together

1. The post title.
2. A line of placeholders for the post's photos, plus any photos OP posted in comments before
   saying it worked.
3. OP's own text from before the fix: passages from the post body, then from OP's comments posted
   before the confirmation, such as answers to "how often do you water?".

Line breaks inside a passage became single spaces. Passages are separated by blank lines.

Photos are numbered in reading order: question, then answer, then outcome. Answers never contain
photos. `{Image_NN}` stands for the file in column `Image_NN` of the same row. Literal `{` and `}`
from Reddit are doubled (`{{`, `}}`), so `str.format` both fills the placeholders and restores
the original braces.

## Guaranteed by the build code (checked on all 96 rows)

1. **Verbatim.** Every passage is an exact substring of the comment it came from; only whitespace
   was collapsed. Nothing was paraphrased.
2. **Right author.** `question` and `outcome` contain only OP's text; `answer` never does.
3. **Right order in time.** Everything in `question` and `answer` was posted before OP's
   confirming comment, and everything in `outcome` was posted at that time or later. So the
   question never reveals the fix or the result, and the answer never contains advice given after
   OP said it worked.
4. **Placeholders match files.** Each `{Image_NN}` in the text has a filled `Image_NN` column and
   the file exists. Each filled column is used in the text.
5. **Safe to format.** `field.format(**{c: ... for c in image_cols})` works on every field of every
   row.
6. **No eval overlap.** The 13 threads in `data/reddit/cases.csv` (the Reddit eval cases) are not
   in this file.

## Before using it as eval data

- **Never give a model under test anything but `question` and its photos.** `answer` and
  `outcome` are the reference. `plant`, `problem` and `advice_summary` were written by Claude after
  reading the whole thread, outcome included, so they give the answer away. Use them as metadata
  or as a reference diagnosis only. The same goes for the `*_sources` and `*_url` columns.
- **The labels come from an LLM.** Claude Sonnet 5.5 decided which threads are "advice that
  worked" (96 of 7,514 scraped threads). By hand, about 90 of the 96 are clear-cut. These five are
  borderline and you may want to drop them: `1gj7tyl`, `1kbiakb`, `1bytyxl`, `1ao6rfb`, `1u3kg0t`.
- **"Worked" is OP's own word,** often given within days. It is not an expert diagnosis, and
  `answer` may hold several suggestions of which OP followed only some.
- **The text is raw Reddit:** typos, emoji and leftover markdown such as `**Context**:`. A few rows
  are not in English, e.g. the outcomes of `1l7tndu` (French) and `1028vjv` (Croatian).
- **It is small.** With 96 threads, report confidence intervals. There is no train/test split;
  treat all of it as test data.
- **The photos belong to Reddit users.** The repo is private; keep it that way.

## Loading

From the repo root. Packages: `pandas`, plus `anthropic`, `Pillow` and `python-dotenv` for
`diagnose.image_block`, and `google-genai` for Gemini.

```python
import pandas as pd

df = pd.read_csv("data/reddit/resolved/threads.csv", dtype=str, keep_default_na=False)
IMAGE_COLS = [c for c in df.columns if c.startswith("Image_")]

def to_parts(text, row):
    """Split a field into ("text", str) and ("image", path) pieces, in reading order."""
    marked = text.format(**{c: f"\0{c}\0" for c in IMAGE_COLS})
    return [("image", row[p]) if i % 2 else ("text", p)
            for i, p in enumerate(marked.split("\0")) if i % 2 or p.strip()]

row = df.iloc[0]
plain = row.question.format(**{c: "<image>" for c in IMAGE_COLS})           # text with markers
photos = [v for k, v in to_parts(row.question, row) if k == "image"]       # the question's photos
```

**Claude**, with each photo placed where it appears in the text. `diagnose.image_block` shrinks a
photo to at most 1568 px and re-encodes it as JPEG, which the 4.5 MB originals need:

```python
import anthropic
from diagnose import image_block

def claude_content(text, row):
    return [image_block(v) if k == "image" else {"type": "text", "text": v} for k, v in to_parts(text, row)]

reply = anthropic.Anthropic().messages.create(
    model="claude-haiku-5-5", max_tokens=16000,
    messages=[{"role": "user", "content": claude_content(row.question, row)}],
)
```

**Gemini**, with the same parts:

```python
from pathlib import Path
from google.genai import types
from llm import MIME

def gemini_parts(text, row):
    return [types.Part.from_bytes(data=Path(v).read_bytes(), mime_type=MIME[Path(v).suffix.lower()])
            if k == "image" else v for k, v in to_parts(text, row)]
```

**Through `diagnose.py`**, which takes photos plus a title and body:

```python
title, _, rest = row.question.format(**{c: "" for c in IMAGE_COLS}).partition("\n\n")
args = [a for p in photos for a in ("--image", p)] + ["--title", title, "--body", rest.strip()]
# python diagnose.py <args> --mode llm --out results/llm/reddit_<thread_id>.json
```

**Scoring:** compare the model's diagnosis and advice to `answer` (what worked) and `problem` (the
confirmed diagnosis). `outcome` shows what OP actually did, which helps judge whether the model's
advice would have led to the same fix.

## Rebuilding

`python reddit/release.py` rebuilds this folder (CSV and `images/`) from the raw scrape in
`reddit/data/`. That scrape is not in git; `reddit/README.md` has the full pipeline.
