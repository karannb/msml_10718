import math
import re

import numpy as np
import pandas as pd
import requests

from harness import rules
from harness.data import corpus

rng = np.random.default_rng(10718)


def r4(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p, d = k / n, 1 + z * z / n
    c, h = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [r4((c - h) / d), r4((c + h) / d)]


def bootstrap_ci(stat, n, reps=2000):
    idx = rng.integers(0, n, (reps, n))
    return [r4(v) for v in np.percentile([stat(i) for i in idx], [2.5, 97.5])]


def classification(true, pred, labels):
    """true/pred: label lists; a prediction outside `labels` (or missing) counts as wrong."""
    K = len(labels)
    y = np.array([labels.index(t) for t in true])
    p = np.array([labels.index(q) if q in labels else K for q in pred])
    cm = np.bincount(y * (K + 1) + p, minlength=K * (K + 1)).reshape(K, K + 1)
    recall = lambda yy, pp: np.array([(pp[yy == k] == k).mean() for k in range(K) if (yy == k).any()])
    tp, support, predicted = np.diag(cm[:, :K]), cm.sum(1), cm[:, :K].sum(0)
    prec = np.divide(tp, predicted, out=np.zeros(K), where=predicted > 0)
    rec = np.divide(tp, support, out=np.zeros(K), where=support > 0)
    return dict(
        n=len(y), accuracy=r4((y == p).mean()), accuracy_ci=bootstrap_ci(lambda i: (y[i] == p[i]).mean(), len(y)),
        balanced_accuracy=r4(recall(y, p).mean()), balanced_accuracy_ci=bootstrap_ci(lambda i: recall(y[i], p[i]).mean(), len(y)),
        majority_class_accuracy=r4(support.max() / len(y)),
        per_class={l: dict(precision=r4(prec[i]), recall=r4(rec[i]), n=int(support[i])) for i, l in enumerate(labels)},
        confusion={t: {q: int(cm[i, j]) for j, q in enumerate(labels + ["no_answer"]) if cm[i, j]} for i, t in enumerate(labels)},
    )


def mcnemar(ours, theirs):
    # Exact two-sided test on the cases where exactly one system is right.
    a, b = int((ours & ~theirs).sum()), int((~ours & theirs).sum())
    n, k = a + b, min(a, b)
    return dict(only_this_correct=a, only_baseline_correct=b, p=float(f"{min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0:.3g}"))


def norm_url(u):
    return re.sub(r"^(https?://)?(www\.)?", "", u.strip().lower()).rstrip("/")


def remedies(df, check_urls=False):
    """df rows: label (true), remedies. Rule-based harm flags, generic phrases and citations."""
    use = {norm_url(u): x for u, x in zip(corpus().url, corpus().use)}
    rows = []
    for r in df[df.remedies.notna()].itertuples():
        text = " ".join(x["action"] for x in r.remedies)
        urls = [norm_url(x["source_url"]) for x in r.remedies if x.get("source_url")]
        rows.append(rules.flags(text, r.label) | dict(
            steps=len(r.remedies), generic=sum(len(g.findall(text.lower())) for g in rules.GENERIC), urls=urls,
            in_corpus=sum(u in use for u in urls), gold_source=sum(use.get(u) == "holdout_gold" for u in urls),
            reputable=sum(u in use or bool(rules.REPUTABLE.search(u.split("/")[0] + "/")) for u in urls)))
    if not rows:
        return None
    m = pd.DataFrame(rows)
    flag_cols = list(rules.flags("", "healthy"))
    cited = m.urls.map(len).sum()
    out = dict(
        answered=len(m), steps_per_answer=r4(m.steps.mean()),
        harm_flags={c: r4(m[c].mean()) for c in flag_cols},
        any_harm_flag=r4(m[flag_cols].any(axis=1).mean()), severe_harm_flag=r4(m[rules.SEVERE].any(axis=1).mean()),
        generic_per_answer=r4(m.generic.mean()),
        citations=dict(steps_cited=r4(cited / m.steps.sum()) if m.steps.sum() else None,
                       **{k: r4(m[k].sum() / cited) if cited else None for k in ["in_corpus", "reputable", "gold_source"]}),
    )
    if check_urls and cited:
        ok = {u: url_ok(u) for u in {u for us in m.urls for u in us}}
        out["citations"]["reachable"] = r4(np.mean([ok[u] for us in m.urls for u in us]))
    return out


def url_ok(u):
    try:
        return requests.get("https://" + u, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, stream=True).status_code < 400
    except requests.RequestException:
        return False


def judged(verdicts):
    ok = pd.DataFrame([v for v in verdicts.values() if "error" not in v])
    out = dict(n=len(verdicts), errors=len(verdicts) - len(ok))
    if len(ok):
        axes = ["harmfulness", "specificity_accuracy", "feasibility"]
        out |= dict(mean={a: r4(ok[a].mean()) for a in axes},
                    safe_and_useful=r4((ok[axes] >= 4).all(axis=1).mean()), severe_harm=r4((ok.harmfulness <= 2).mean()),
                    diagnosis_match=r4(ok.diagnosis_match.map({"yes": 1, "partial": 0.5, "no": 0}).mean()))
    return out


def business(df, price_in=None, price_out=None):
    """df rows: stages, label, pred. Error rate, latency, cost and expected error cost."""
    names = sorted({s for st in df.stages for s in st})
    stage = lambda name, key: pd.Series([st.get(name, {}).get(key) for st in df.stages], dtype=float)
    total = sum(stage(s, "latency_ms") for s in names)
    out = dict(requests=len(df), error_rate=r4(pd.Series([any("error" in v for v in st.values()) for st in df.stages]).mean()),
               latency_ms=dict(p50=r4(total.quantile(.5)), p95=r4(total.quantile(.95))))
    cost = sum(stage(s, "cost_usd").fillna(0) for s in names)
    if not cost.any() and price_in is not None and price_out is not None:
        tok = lambda k: sum(stage(s, k).fillna(0) for s in names)
        cost = (tok("input_tokens") * price_in + tok("output_tokens") * price_out) / 1e6
    if cost.any():
        out["cost_usd_per_1000"] = r4(cost.mean() * 1000)
    if df.pred.isin(["healthy", "watering", "fungal_bacterial", "pest", "other"]).any():
        out["expected_error_cost"] = r4(np.mean([rules.error_cost(t, p) for t, p in zip(df.label, df.pred)]))
    return out
