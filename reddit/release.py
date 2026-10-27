"""Write the resolved threads as an eval-ready CSV, with their images, to data/reddit/resolved/.

    uv run python release.py

threads.csv has one row per thread. question / answer / outcome are the verbatim one-turn
passages (see label.py oneturn), with images as placeholders {Image_01}, {Image_02}, ...:
the post's photos follow the title, and photos OP linked in a comment replace the link.
Column Image_NN holds that image's path relative to the repo root (empty when a thread has
fewer images). Braces in the Reddit text are doubled, so str.format fills the placeholders:

    images = {c: row[c] for c in df.columns if c.startswith("Image_")}
    prompt = row["question"].format(**{c: "<image>" for c in images})
"""

import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path

from common import COMMENT_IMG_RE, DATA, SUBREDDITS
from label import records

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "reddit" / "resolved"


def esc(text):
    return text.replace("{", "{{").replace("}", "}}")


def to_row(rec, img_dir):
    images, tags = [], {}  # data/-relative source paths in placeholder order; url -> placeholder

    def tag(im):
        if im["url"] not in tags:
            images.append(im["path"])
            tags[im["url"]] = f"{{Image_{len(images):02d}}}"
        return tags[im["url"]]

    op_photos = {im["url"]: im for im in rec["op_images"]}

    def with_tags(text):
        return COMMENT_IMG_RE.sub(lambda m: tag(op_photos[m[0]]) if m[0] in op_photos else m[0], esc(text))

    def photos_of(part):
        """Placeholders for photos OP posted in this field's source comments (e.g. "after" photos
        in the confirming comment) that the selected passages don't already link."""
        return [tag(im) for im in rec["op_images"]
                if im["comment_id"] in rec[f"{part}_sources"] and im["url"] not in rec[part]]

    body = rec["question"].removeprefix(rec["title"]).lstrip("\n")  # question = title + OP's passages
    question_tags = [tag(im) for im in rec["images"]] + photos_of("question")
    question = "\n\n".join(filter(None, [esc(rec["title"]), " ".join(question_tags), with_tags(body)]))
    answer = with_tags(rec["answer"])
    outcome = "\n\n".join(filter(None, [with_tags(rec["outcome"]), " ".join(photos_of("outcome"))]))

    row = {
        "thread_id": rec["id"],
        "subreddit": rec["subreddit"],
        "created": datetime.fromtimestamp(rec["created_utc"], timezone.utc).strftime("%Y-%m-%d"),
        "url": rec["permalink"],
        "question": question,
        "answer": answer,
        "outcome": outcome,
        "plant": rec["plant"],
        "problem": rec["problem"],
        "advice_summary": rec["advice"],
        "community_agrees": rec["community_agrees"],
        "n_images": len(images),
        "question_sources": ";".join(rec["question_sources"]),
        "answer_sources": ";".join(rec["answer_sources"]),
        "outcome_sources": ";".join(rec["outcome_sources"]),
        "advice_comment_url": rec["advice_comment_url"],
        "outcome_comment_url": rec["op_evidence_url"],
    }
    for k, src in enumerate(images, 1):
        dst = img_dir / f"{rec['id']}_{k:02d}{Path(src).suffix}"
        shutil.copy2(DATA / src, dst)
        row[f"Image_{k:02d}"] = str(dst.relative_to(REPO))
    return row


def main():
    img_dir = OUT / "images"
    if img_dir.exists():
        shutil.rmtree(img_dir)  # rebuilt from data/ every time
    img_dir.mkdir(parents=True)
    rows = [to_row(rec, img_dir) for rec in records(SUBREDDITS, {"resolved"})]
    n_img = max(r["n_images"] for r in rows)
    fields = list(rows[0])[:17] + [f"Image_{k:02d}" for k in range(1, n_img + 1)]
    with open(OUT / "threads.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, restval="")
        w.writeheader()
        w.writerows(rows)
    size = sum(p.stat().st_size for p in img_dir.iterdir())
    print(f"{len(rows)} threads, {sum(r['n_images'] for r in rows)} images ({size / 1e6:.0f} MB), "
          f"up to {n_img} per thread -> {OUT.relative_to(REPO)}/")


if __name__ == "__main__":
    main()
