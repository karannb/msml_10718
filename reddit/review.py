"""Build data/review.html, a page for eyeballing labelled threads quickly, and serve it.

    uv run python review.py                                          # the resolved threads (the dataset)
    uv run python review.py --labels diagnosis_confirmed --sample 100

Serves data/ on http://127.0.0.1:8765 (this machine only) and opens the page; Ctrl-C stops.
Opening review.html directly as a file shows no photos when the browser lacks macOS
permission to read ~/Desktop, which the server sidesteps.

One thread at a time: photos, post, Claude's extraction, the advice comment and OP's
confirmation. Keys: left/right move, g / b / u mark good / bad / unsure (and advance),
n jumps to the next unmarked thread. Marks stay in the browser (localStorage) across
reloads and rebuilds; "Export marks" downloads them as review_marks.json.
"""

import argparse
import functools
import http.server
import json
import random
import webbrowser

from common import DATA, SUBREDDITS
from label import records

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Thread review</title>
<style>
:root { --bg:#f6f5f1; --card:#ffffff; --ink:#1d1d1b; --muted:#6c6b66; --line:#e2e0d9;
        --accent:#2f6f4e; --good:#2f7d4f; --bad:#b4442f; --unsure:#9a7412; --advice:#edf5ef; --op:#fbf3e2; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#141513; --card:#1d1e1b; --ink:#e8e7e2; --muted:#9a9990; --line:#33342f;
          --accent:#7cc59b; --good:#5fb882; --bad:#e07d68; --unsure:#d9b24a; --advice:#1d2a22; --op:#2b2619; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; }
a { color: var(--accent); }
header { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
         padding: 10px 16px; display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
header h1 { font-size: 16px; margin: 0; }
.stats { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
.stats b { color: var(--ink); font-weight: 600; }
select, button, input { font: inherit; font-size: 14px; color: var(--ink); background: var(--card);
                        border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px; }
button { cursor: pointer; }
.spacer { flex: 1; }
main { max-width: 980px; margin: 0 auto; padding: 16px; }
.pos { font-size: 13px; color: var(--muted); margin-bottom: 8px; display: flex; gap: 8px; align-items: center; }
.card { background: var(--card); border: 2px solid var(--line); border-radius: 10px; padding: 18px 20px; }
.card.good { border-color: var(--good); } .card.bad { border-color: var(--bad); } .card.unsure { border-color: var(--unsure); }
.meta { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: center; }
.chip { border: 1px solid var(--line); border-radius: 999px; padding: 0 8px; }
h2 { font-size: 20px; line-height: 1.3; margin: 8px 0 12px; }
.imgs { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.imgs figure { margin: 0; flex: 0 0 auto; }
.imgs img { height: 240px; border-radius: 6px; display: block; cursor: zoom-in; background: var(--line); }
.imgs figcaption { font-size: 12px; color: var(--muted); max-width: 240px; }
.body { white-space: pre-wrap; max-height: 200px; overflow: auto; margin: 12px 0; }
dl { display: grid; grid-template-columns: 80px 1fr; gap: 2px 12px; margin: 14px 0; font-size: 14px; }
dt { color: var(--muted); } dd { margin: 0; }
.comment { border-left: 3px solid var(--line); border-radius: 4px; padding: 8px 12px; margin: 10px 0; white-space: pre-wrap; }
.comment.advice { background: var(--advice); border-color: var(--accent); }
.comment.op { background: var(--op); border-color: var(--unsure); }
.who { font-size: 12px; color: var(--muted); display: flex; justify-content: space-between; margin-bottom: 4px; white-space: normal; }
.sub { font-size: 13px; color: var(--muted); margin: 14px 0 6px; }
.reason { font-size: 13px; color: var(--muted); font-style: italic; margin: 12px 0 0; }
.bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 14px; }
.bar button.on.good { background: var(--good); border-color: var(--good); color: #fff; }
.bar button.on.bad { background: var(--bad); border-color: var(--bad); color: #fff; }
.bar button.on.unsure { background: var(--unsure); border-color: var(--unsure); color: #fff; }
.bar input { flex: 1; min-width: 180px; }
details { margin-top: 14px; } summary { cursor: pointer; color: var(--muted); font-size: 14px; }
details pre { white-space: pre-wrap; font-size: 13px; max-height: 420px; overflow: auto; }
.keys { font-size: 12px; color: var(--muted); margin-top: 12px; }
kbd { border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; font-size: 11px; background: var(--card); }
#lightbox { position: fixed; inset: 0; z-index: 5; background: rgba(0,0,0,.88); display: none;
            align-items: center; justify-content: center; cursor: zoom-out; }
#lightbox img { max-width: 96vw; max-height: 96vh; }
@media (max-width: 600px) { .imgs img { height: 170px; } dl { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>Thread review</h1>
  <select id="fsub" aria-label="Subreddit"></select>
  <select id="flabel" aria-label="Label"></select>
  <select id="fmark" aria-label="Mark">
    <option value="all">all marks</option><option value="none">unmarked</option>
    <option value="good">good</option><option value="bad">bad</option><option value="unsure">unsure</option>
  </select>
  <span class="stats" id="stats"></span>
  <span class="spacer"></span>
  <button id="export">Export marks</button>
</header>
<main>
  <div class="pos"><button id="prev" aria-label="Previous">&larr;</button><span id="pos"></span><button id="next" aria-label="Next">&rarr;</button></div>
  <div id="card"></div>
  <p class="keys"><kbd>&larr;</kbd> <kbd>&rarr;</kbd> move &middot; <kbd>g</kbd> good &middot; <kbd>b</kbd> bad &middot;
     <kbd>u</kbd> unsure &middot; <kbd>n</kbd> next unmarked &middot; click a photo to enlarge</p>
</main>
<div id="lightbox"><img alt=""></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const STORE = 'plant-review-marks';
let marks = {};
try { marks = JSON.parse(localStorage.getItem(STORE) || '{}'); } catch (e) {}
const save = () => { try { localStorage.setItem(STORE, JSON.stringify(marks)); } catch (e) {} };
const $ = id => document.getElementById(id);
let view = [], i = 0;

function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') n.className = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const k of kids.flat(Infinity)) if (k) n.append(k);  // strings become text nodes, never HTML
  return n;
}

function options(select, label, values) {
  select.replaceChildren(el('option', {value: ''}, label), ...values.map(v => el('option', {value: v}, v)));
  select.hidden = values.length < 2;
}
options($('fsub'), 'all subreddits', [...new Set(DATA.map(r => r.subreddit))]);
options($('flabel'), 'all labels', [...new Set(DATA.map(r => r.label))]);

function refilter() {
  const cur = view[i] && view[i].id;
  const sub = $('fsub').value, lab = $('flabel').value, mk = $('fmark').value;
  view = DATA.filter(r => (!sub || r.subreddit === sub) && (!lab || r.label === lab) &&
    (mk === 'all' || (mk === 'none' ? !(marks[r.id] || {}).verdict : (marks[r.id] || {}).verdict === mk)));
  const j = view.findIndex(r => r.id === cur);
  i = j >= 0 ? j : Math.min(i, Math.max(view.length - 1, 0));
}

function stats() {
  const c = {good: 0, bad: 0, unsure: 0};
  for (const r of DATA) { const v = (marks[r.id] || {}).verdict; if (v) c[v]++; }
  const left = DATA.length - c.good - c.bad - c.unsure;
  $('stats').replaceChildren(el('b', {}, String(DATA.length)), ' threads · ', el('b', {}, String(c.good)), ' good · ',
    el('b', {}, String(c.bad)), ' bad · ', el('b', {}, String(c.unsure)), ' unsure · ', el('b', {}, String(left)), ' left');
}

function zoom(src) { $('lightbox').querySelector('img').src = src; $('lightbox').style.display = 'flex'; }
$('lightbox').onclick = () => { $('lightbox').style.display = 'none'; };

const photos = list => el('div', {class: 'imgs'}, list.map(im =>
  el('figure', {}, el('img', {src: im.path, loading: 'lazy', alt: im.caption || 'post photo', onclick: () => zoom(im.path)}),
     im.caption ? el('figcaption', {}, im.caption) : null)));

const comment = (kind, title, text, url) => el('div', {class: 'comment ' + kind},
  el('div', {class: 'who'}, el('span', {}, title), el('a', {href: url, target: '_blank', rel: 'noopener'}, 'permalink ↗')),
  (text || '(comment not found)').replace(/https?:\/\/(preview|i)\.redd\.it\/\S+/g, '[photo]'));

function render() {
  stats();
  $('pos').textContent = view.length ? `${i + 1} / ${view.length}` : '0 / 0';
  if (!view.length) { $('card').replaceChildren(el('div', {class: 'card'}, 'Nothing matches these filters.')); return; }
  const r = view[i], m = marks[r.id] || {};
  try { history.replaceState(null, '', '#' + r.id); } catch (e) {}
  const date = new Date(r.created_utc * 1000).toISOString().slice(0, 10);
  $('card').replaceChildren(el('article', {class: 'card ' + (m.verdict || '')},
    el('div', {class: 'meta'}, el('span', {class: 'chip'}, 'r/' + r.subreddit), date,
       r.flair ? el('span', {class: 'chip'}, r.flair) : null, el('span', {class: 'chip'}, r.label),
       el('a', {href: r.permalink, target: '_blank', rel: 'noopener'}, 'open on Reddit ↗')),
    el('h2', {}, r.title),
    photos(r.images),
    r.selftext ? el('div', {class: 'body'}, r.selftext) : null,
    el('dl', {}, el('dt', {}, 'plant'), el('dd', {}, r.plant || '—'), el('dt', {}, 'problem'), el('dd', {}, r.problem || '—'),
       el('dt', {}, 'advice'), el('dd', {}, r.advice || '—')),
    r.question ? [
      comment('', 'Question: verbatim from the post + OP comments before the fix', r.question, r.permalink),
      comment('advice', 'Answer: verbatim from commenters, posted before OP confirmed', r.answer, r.advice_comment_url),
      comment('op', 'Outcome: verbatim from OP', r.outcome, r.op_evidence_url),
    ] : [
      comment('advice', 'Advice OP responded to', r.advice_comment, r.advice_comment_url),
      comment('op', "OP's confirmation", r.op_evidence_comment, r.op_evidence_url),
    ],
    r.op_images.length ? [el('div', {class: 'sub'}, 'Photos OP posted in comments'), photos(r.op_images)] : null,
    el('p', {class: 'reason'}, 'Claude: ' + r.reason),
    el('div', {class: 'bar'},
      ['good', 'bad', 'unsure'].map(v => el('button', {class: v + (m.verdict === v ? ' on' : ''), onclick: () => mark(v)}, `${v} (${v[0]})`)),
      el('input', {placeholder: 'note (optional)', value: m.note || '', 'aria-label': 'Note',
                   oninput: e => { marks[r.id] = {...(marks[r.id] || {}), note: e.target.value}; save(); }})),
    el('details', {}, el('summary', {}, 'Full thread'), el('pre', {}, r.thread_text))));
}

function go(d) { if (view.length) { i = Math.min(Math.max(i + d, 0), view.length - 1); render(); scrollTo(0, 0); } }

function mark(v) {
  const r = view[i]; if (!r) return;
  const cur = marks[r.id] || {};
  marks[r.id] = {...cur, verdict: cur.verdict === v ? null : v};
  save();
  if ($('fmark').value === 'all') go(1);
  else { const was = i; refilter(); i = Math.min(was, Math.max(view.length - 1, 0)); render(); }
}

function nextUnmarked() {
  for (let k = 1; k <= view.length; k++) {
    const j = (i + k) % view.length;
    if (!(marks[view[j].id] || {}).verdict) { i = j; render(); scrollTo(0, 0); return; }
  }
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { $('lightbox').style.display = 'none'; document.activeElement.blur(); return; }
  if (e.target.matches('input, select, textarea') || e.metaKey || e.ctrlKey || e.altKey) return;
  const act = {ArrowRight: () => go(1), ArrowLeft: () => go(-1), g: () => mark('good'), b: () => mark('bad'),
               u: () => mark('unsure'), n: nextUnmarked}[e.key];
  if (act) { e.preventDefault(); act(); }
});
$('prev').onclick = () => go(-1);
$('next').onclick = () => go(1);
for (const id of ['fsub', 'flabel', 'fmark']) $(id).onchange = () => { refilter(); render(); };

$('export').onclick = () => {
  const out = {};
  for (const r of DATA) if (marks[r.id] && (marks[r.id].verdict || marks[r.id].note))
    out[r.id] = {subreddit: r.subreddit, label: r.label, title: r.title, permalink: r.permalink, ...marks[r.id]};
  const a = el('a', {href: URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {type: 'application/json'})),
                     download: 'review_marks.json'});
  a.click();
};

refilter();
const start = DATA.findIndex(r => '#' + r.id === location.hash);
if (start >= 0) { i = view.findIndex(r => r.id === DATA[start].id); if (i < 0) i = 0; }
render();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subs", nargs="+", default=SUBREDDITS)
    ap.add_argument("--labels", nargs="+", default=["resolved"])
    ap.add_argument("--sample", type=int, help="random sample of this many threads")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--port", type=int, default=8765, help="keep it fixed: marks are stored per address")
    ap.add_argument("--no-serve", action="store_true", help="only write the HTML file")
    args = ap.parse_args()
    recs = list(records(args.subs, set(args.labels)))
    if args.sample and args.sample < len(recs):
        recs = random.Random(args.seed).sample(recs, args.sample)
    data = json.dumps(recs, ensure_ascii=False).replace("</", "<\\/")  # keep </script> out of the JSON
    out = DATA / "review.html"  # image paths in the records are relative to data/
    out.write_text(PAGE.replace("__DATA__", data))
    print(f"{len(recs)} threads -> {out}")
    if args.no_serve:
        return

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(Quiet, directory=DATA))
    url = f"http://127.0.0.1:{args.port}/review.html"
    print(f"serving {url}  (Ctrl-C to stop)", flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
