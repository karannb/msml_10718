"""Shared pieces: Arctic Shift (Reddit archive) client, post/comment helpers, thread rendering."""

import html
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

API = "https://arctic-shift.photon-reddit.com/api"
UA = "cmu-10718-plant-health-research/0.1"  # the default Python UA gets a 403
DATA = Path(__file__).parent / "data"
SUBREDDITS = ["plantclinic", "houseplants", "plants"]

COMMENT_FIELDS = "id,author,parent_id,body,created_utc,score"
SKIP_AUTHORS = {"[deleted]", "AutoModerator"}
GONE = {"[deleted]", "[removed]"}

# Hand-picked threads from the MSML baseline report. They are the recommendation eval
# set, so they may appear as few-shot examples for the filter but never in the dataset.
EVAL_THREADS = {
    "1qi9aql", "jh8zd3", "1ehk66b", "1dva9n1", "17ni5fi", "n0th2v", "l9ee0e",
    "17zk3gw", "ljowuk", "jlrgdh", "1v62jzs", "1n190yj", "1m5ndp4",
}


def api_get(endpoint, **params):
    """GET an Arctic Shift endpoint and return its `data` list, retrying on 429/5xx."""
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                body = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            time.sleep(float(e.headers.get("x-ratelimit-reset") or 2**attempt))
            continue
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2**attempt)
            continue
        if body.get("error"):
            raise RuntimeError(f"{url}: {body['error']}")
        return body["data"] or []
    raise RuntimeError(f"giving up on {url}")


def fetch_comments(post_id, max_pages=10):
    """All archived comments of a thread, oldest first."""
    out, seen, after = [], set(), None
    for _ in range(max_pages):
        params = dict(link_id=post_id, limit=100, sort="asc", fields=COMMENT_FIELDS)
        if after is not None:
            params["after"] = after
        page = api_get("comments/search", **params)
        out += [c for c in page if c["id"] not in seen]
        seen.update(c["id"] for c in page)
        if len(page) < 100:
            break
        after = page[-1]["created_utc"]
    return out


def _largest_upto(resolutions, width, key_w, key_u):
    fits = [r for r in resolutions if r.get(key_w, 0) <= width and r.get(key_u)]
    return html.unescape(max(fits, key=lambda r: r[key_w])[key_u]) if fits else None


def image_urls(post, width=1080):
    """[{url, preview, caption}] for a post's images (gallery items, else the linked image).

    `url` is the full-size original; `preview` is Reddit's resized copy at most `width` px wide
    (None if Reddit made none).
    """
    meta = post.get("media_metadata") or {}
    items = (post.get("gallery_data") or {}).get("items") or []
    imgs = []
    for it in items:
        m = meta.get(it.get("media_id")) or {}
        if m.get("status") == "valid" and m.get("e") == "Image" and m.get("s", {}).get("u"):
            imgs.append({"url": html.unescape(m["s"]["u"]),
                         "preview": _largest_upto(m.get("p") or [], width, "x", "u"),
                         "caption": it.get("caption") or ""})
    if imgs:
        return imgs
    url = post.get("url") or ""
    previews = (post.get("preview") or {}).get("images") or []
    preview = _largest_upto(previews[0].get("resolutions") or [], width, "width", "url") if previews else None
    if post.get("post_hint") == "image" or url.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        return [{"url": url, "preview": preview, "caption": ""}]
    if previews and previews[0].get("source", {}).get("url"):
        return [{"url": html.unescape(previews[0]["source"]["url"]), "preview": preview, "caption": ""}]
    return []


IMG_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
COMMENT_IMG_RE = re.compile(r"https?://(?:preview\.redd\.it|i\.redd\.it|i\.imgur\.com)/[^\s)\]]+")


def download_image(url, stem):
    """Save an image to `stem` + extension; return the path, or None if it is gone.

    Deleted Reddit/Imgur images come back as 404s, redirects to a "removed" placeholder,
    or tiny non-image responses, so anything that is not a real image file counts as gone.
    """
    req = urllib.request.Request(html.unescape(url), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ctype, final, data = r.headers.get_content_type(), r.geturl(), r.read()
    except (OSError, ValueError, http.client.HTTPException):
        return None
    if ctype not in IMG_EXT or len(data) < 5000 or "removed" in final:
        return None
    path = stem.with_suffix(IMG_EXT[ctype])
    path.write_bytes(data)
    return path


def slim_post(p):
    return {
        "id": p["id"],
        "subreddit": p["subreddit"],
        "author": p["author"],
        "title": p.get("title") or "",
        "selftext": p.get("selftext") or "",
        "created_utc": p["created_utc"],
        "flair": p.get("link_flair_text") or "",
        "url": p.get("url") or "",
        "permalink": f"https://www.reddit.com/r/{p['subreddit']}/comments/{p['id']}/",
        "images": image_urls(p),
    }


def is_candidate(post, comments):
    """Stage-1 filter: OP replied to a (still visible) comment from another user."""
    op = post["author"]
    if op in SKIP_AUTHORS:
        return False
    by_id = {c["id"]: c for c in comments}
    for c in comments:
        if c["author"] != op or not c["parent_id"].startswith("t1_"):
            continue
        parent = by_id.get(c["parent_id"][3:])
        if parent and parent["author"] not in SKIP_AUTHORS | {op} and parent["body"] not in GONE:
            return True
    return False


def fetch_thread(post_id):
    """(slim post, comments) for one thread, straight from the archive."""
    posts = api_get("posts/ids", ids=post_id)
    if not posts:
        raise RuntimeError(f"post {post_id} not in archive")
    return slim_post(posts[0]), fetch_comments(post_id)


def _clip(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + " …[truncated]"


def _since(post, c):
    h = (c["created_utc"] - post["created_utc"]) / 3600
    return f" (+{h:.0f}h)" if h < 48 else f" (+{h / 24:.0f}d)"


def render_thread(post, comments, max_roots=12, max_chars=1000, max_other=5, show_times=False):
    """Plain-text view of a thread for the LLM filter.

    Shows the post, then every comment chain that leads to an OP comment together with the
    replies under OP's comments, then a few other top-level replies so the model can judge
    agreement.
    Usernames are replaced with OP / user1 / user2 ...; `show_times` adds each comment's
    age relative to the post, e.g. (+5h).
    """
    when = (lambda c: _since(post, c)) if show_times else (lambda c: "")
    op = post["author"]
    names = {op: "OP"}

    def name(author):
        if author in SKIP_AUTHORS:
            return author
        return names.setdefault(author, f"user{len(names)}")

    by_id = {c["id"]: c for c in comments}
    children = defaultdict(list)
    for c in sorted(comments, key=lambda c: c["created_utc"]):
        children[c["parent_id"]].append(c)

    keep = set()  # OP comments and all their ancestors
    for c in comments:
        node = c if c["author"] == op else None
        while node and node["id"] not in keep:
            keep.add(node["id"])
            pid = node["parent_id"]
            node = by_id.get(pid[3:]) if pid.startswith("t1_") else None
    # ...plus everything posted under an OP comment, so answers to OP's follow-up questions show
    stack = [c for c in comments if c["author"] == op]
    while stack:
        for ch in children[f"t1_{stack.pop()['id']}"]:
            if ch["id"] not in keep:
                keep.add(ch["id"])
                stack.append(ch)

    def is_root(c):
        return c["parent_id"] == f"t3_{post['id']}" or c["parent_id"][3:] not in by_id

    roots = sorted((by_id[i] for i in keep if is_root(by_id[i])), key=lambda c: c["created_utc"])

    lines = []

    def walk(c, depth):
        missing = "" if c["parent_id"][3:] in by_id or c["parent_id"].startswith("t3_") else " (reply to a comment no longer available)"
        lines.append(f"{'  ' * depth}[{c['id']}] {name(c['author'])}{when(c)}{missing}: {_clip(c['body'], max_chars)}")
        for ch in children[f"t1_{c['id']}"]:
            if ch["id"] in keep:
                walk(ch, depth + 1)

    date = datetime.fromtimestamp(post["created_utc"], timezone.utc).strftime("%Y-%m-%d")
    captions = [i["caption"] for i in post["images"] if i["caption"]]
    head = [
        f"r/{post['subreddit']} | posted {date}" + (f" | flair: {post['flair']}" if post["flair"] else ""),
        f"TITLE: {post['title']}",
        f"BODY: {_clip(post['selftext'], 2 * max_chars) or '(none)'}",
        f"IMAGES: {len(post['images'])}" + (f" (captions: {'; '.join(captions)})" if captions else ""),
        "",
        "COMMENT CHAINS INVOLVING OP:",
    ]
    for r in roots[:max_roots]:
        walk(r, 1)
        lines.append("")
    if len(roots) > max_roots:
        lines.append(f"  ({len(roots) - max_roots} more chains omitted)")

    others = [c for c in children[f"t3_{post['id']}"] if c["id"] not in keep and c["body"] not in GONE][:max_other]
    if others:
        lines.append("OTHER TOP-LEVEL REPLIES (OP did not respond):")
        lines += [f"  [{c['id']}] {name(c['author'])}{when(c)}: {_clip(c['body'], max_chars // 2)}" for c in others]

    return "\n".join(head + lines).rstrip()


def read_jsonl(path):
    if not Path(path).exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
