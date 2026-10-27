"""Stage 1: crawl plant subreddits from the Arctic Shift archive, keeping threads where OP
replied to another user's comment and whose photos can still be downloaded.

Months are visited newest first (older images are increasingly deleted). In each month we
visit random days (seeded) until --per-month threads are kept, which spreads the sample over
seasons; a subreddit stops once it has --target threads. Re-running resumes: checked posts
are skipped and full months are not revisited, so raising --target or --per-month tops up.

    uv run python scrape.py                                  # defaults below
    uv run python scrape.py --subs plantclinic --target 4000

Outputs, per subreddit, under data/<sub>/:
    threads.jsonl  {"post": ..., "comments": [...], "op_images": [...]} per kept thread;
                   post["images"][i]["path"] and op_images[j]["path"] are relative to data/
    images/        post photos (~1080px wide unless --full-res) and photos OP linked in comments
    seen.txt       ids of every post already checked
"""

import argparse
import calendar
import json
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

from common import (COMMENT_IMG_RE, DATA, EVAL_THREADS, GONE, SKIP_AUTHORS, SUBREDDITS, api_get,
                    download_image, fetch_comments, image_urls, is_candidate, read_jsonl, slim_post)

MAX_POST_IMAGES = 10
MAX_COMMENT_IMAGES = 3  # per OP comment

# r/houseplants and r/plants are full of showcase and plant-ID posts; only spend API calls
# on posts that read like a plant-health question (checked against title, body and flair):
# a health keyword, or a generic help/question cue that is not an ID request.
HEALTH_RE = re.compile(
    r"\b(sos|wrong|dying|dead|die[sd]?|sick|sad|sav(e|ing)|rescue|disease\w*|pests?|bugs?|issues?|"
    r"problems?|yellow\w*|brown\w*|spots?|droop\w*|wilt\w*|rot\w*|mold\w*|fung\w*|curl\w*|crisp\w*|"
    r"burn\w*|worried|normal|healthy|over-?water\w*|under-?water\w*|losing|dropping|falling|holes|"
    r"webs?|sticky|struggl\w*|deteriorat\w*|happening|survive\w*|revive|recover\w*)\b"
    r"|how (do|can|to|should) (i |we )?(help|fix|treat)",
    re.I,
)
GENERIC_RE = re.compile(r"\?|\b(help|advice|tips?)\b", re.I)
ID_RE = re.compile(
    r"\bID\b|identif\w*|what (plant|kind|type|species)|name of|what('?s| is) (this|it)\b|know what (this|it) is",
    re.I,
)


def looks_like_health_question(text):
    return bool(HEALTH_RE.search(text) or (GENERIC_RE.search(text) and not ID_RE.search(text)))


def keep_post(p, args):
    if p.get("author") in SKIP_AUTHORS or p.get("over_18") or p.get("removed_by_category"):
        return False
    if (p.get("selftext") or "").strip() in GONE or p["id"] in EVAL_THREADS:
        return False
    text = " ".join([p.get("title") or "", p.get("selftext") or "", p.get("link_flair_text") or ""])
    if not args.all_posts and not looks_like_health_question(text):
        return False
    return bool(image_urls(p))


def process(p, img_dir, full_res):
    """Check one post. Returns (status, thread) with status "no_reply", "no_image" or "kept"."""
    comments = fetch_comments(p["id"])
    if not is_candidate(p, comments):
        return "no_reply", None
    post = slim_post(p)
    for k, im in enumerate(post["images"][:MAX_POST_IMAGES]):
        path = download_image(im["url"] if full_res else im["preview"] or im["url"], img_dir / f"{p['id']}_{k}")
        im["path"] = str(path.relative_to(DATA)) if path else None
    post["images"] = [im for im in post["images"] if im.get("path")]
    if not post["images"]:
        return "no_image", None
    op_images = []  # often "after" photos, useful evidence for resolved threads
    for c in comments:
        if c["author"] != p["author"]:
            continue
        for url in COMMENT_IMG_RE.findall(c["body"])[:MAX_COMMENT_IMAGES]:
            path = download_image(url, img_dir / f"{p['id']}_{c['id']}_{len(op_images)}")
            if path:
                op_images.append({"comment_id": c["id"], "url": url, "path": str(path.relative_to(DATA))})
    return "kept", {"post": post, "comments": comments, "op_images": op_images}


def months(start, end):
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def epoch(d):
    return int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())


def thread_bytes(thread):
    return sum((DATA / im["path"]).stat().st_size for im in thread["post"]["images"] + thread["op_images"])


def scrape_sub(sub, args, budget):
    """Scrape one subreddit; `budget["left"]` is the remaining disk allowance in bytes."""
    out_dir = DATA / sub
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    threads_path, seen_path = out_dir / "threads.jsonl", out_dir / "seen.txt"
    seen = set(seen_path.read_text().split()) if seen_path.exists() else set()
    per_month = Counter(
        datetime.fromtimestamp(t["post"]["created_utc"], timezone.utc).strftime("%Y-%m")
        for t in read_jsonl(threads_path)
    )
    total = sum(per_month.values())

    with open(threads_path, "a") as threads_f, open(seen_path, "a") as seen_f, \
            ThreadPoolExecutor(args.workers) as pool:
        for y, m in reversed(list(months(args.start, args.end))):
            if total >= args.target or budget["left"] <= 0:
                break
            key = f"{y}-{m:02d}"
            found, stats, empty_days = per_month[key], Counter(), 0
            days = list(range(1, calendar.monthrange(y, m)[1] + 1))
            random.Random(f"{args.seed}-{sub}-{key}").shuffle(days)
            for day in days:
                if found >= args.per_month or total >= args.target or budget["left"] <= 0 or empty_days >= 3:
                    break
                d = date(y, m, day)
                posts = api_get("posts/search", subreddit=sub, after=epoch(d),
                                before=epoch(d + timedelta(days=1)), limit=100, sort="asc")
                if not posts:
                    empty_days += 1
                    continue
                todo = [p for p in posts if p["id"] not in seen and keep_post(p, args)]
                futures = {pool.submit(process, p, img_dir, args.full_res): p for p in todo}
                for fut in as_completed(futures):
                    if fut.cancelled():
                        continue  # never ran; stays unseen for a later top-up
                    p = futures[fut]
                    try:
                        status, thread = fut.result()
                    except Exception as e:
                        print(f"  skipping {p['id']}: {e}", flush=True)
                        continue
                    stats[status] += 1
                    seen.add(p["id"])
                    seen_f.write(p["id"] + "\n")
                    if thread:  # threads already in flight when the quota fills are kept too
                        threads_f.write(json.dumps(thread, ensure_ascii=False) + "\n")
                        found += 1
                        total += 1
                        budget["left"] -= thread_bytes(thread)
                    if found >= args.per_month or total >= args.target or budget["left"] <= 0:
                        for f in futures:
                            f.cancel()
                threads_f.flush()
                seen_f.flush()
            per_month[key] = found
            print(f"r/{sub} {key}: {found} kept | this run: {stats['kept']} kept, "
                  f"{stats['no_image']} images gone, {stats['no_reply']} no OP reply", flush=True)
    print(f"r/{sub}: {total} threads -> {threads_path}")


def year_month(s):
    y, m = s.split("-")[:2]
    return int(y), int(m)


def main():
    last = date.today().replace(day=1) - timedelta(days=1)  # leave the current month for late OP replies
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subs", nargs="+", default=SUBREDDITS)
    ap.add_argument("--start", type=year_month, default=(2016, 1), help="oldest month, YYYY-MM (default 2016-01)")
    ap.add_argument("--end", type=year_month, default=(last.year, last.month), help="newest month, YYYY-MM (default last month)")
    ap.add_argument("--target", type=int, default=2500, help="threads to keep per subreddit")
    ap.add_argument("--per-month", type=int, default=40, help="threads to keep per subreddit-month")
    ap.add_argument("--workers", type=int, default=6, help="concurrent thread fetches")
    ap.add_argument("--full-res", action="store_true", help="download original images instead of ~1080px copies")
    ap.add_argument("--all-posts", action="store_true", help="skip the help-request keyword filter")
    ap.add_argument("--max-gb", type=float, default=10, help="stop once data/ reaches this size (default 10)")
    ap.add_argument("--seed", type=int, default=10718)
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    used = sum(f.stat().st_size for f in DATA.rglob("*") if f.is_file())
    budget = {"left": args.max_gb * 1e9 - used}
    for sub in args.subs:
        scrape_sub(sub, args, budget)
        if budget["left"] <= 0:
            print(f"stopped: data/ reached --max-gb {args.max_gb}")
            break


if __name__ == "__main__":
    main()
