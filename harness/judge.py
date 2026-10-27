"""Score advice with prompts/advice_judge.txt on any OpenAI-compatible endpoint (JUDGE_BASE_URL, JUDGE_MODEL,
JUDGE_API_KEY in .env). Verdicts are cached in runs/<run>/judge.jsonl, so re-scoring costs nothing."""

import hashlib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from harness.data import QUESTION, gold

AXES = ["harmfulness", "specificity_accuracy", "feasibility"]


def prompt(r):
    g = gold()[r["label"]]
    reference = "\n".join(f"- {a}" for a in g["advice"]) + "\nSources: " + ", ".join(g["sources"])
    output = f"Health label: {r['pred']}\nCare advice:\n" + "\n".join(
        f"{i}. {x['action']}" + (f" [source: {x['source_url']}]" if x.get("source_url") else "") for i, x in enumerate(r["remedies"], 1))
    case = f"User message: {QUESTION}\nPhoto (described for the judge): condition '{r['orig_label']}'."
    return (Path("prompts/advice_judge.txt").read_text()
            .replace("{case}", case).replace("{reference}", reference).replace("{model_output}", output))


def parse(text):
    v = json.loads(re.search(r"\{\s*\"harmfulness\".*\}", text, re.S).group(0))
    assert all(isinstance(v[a]["score"], int) and 1 <= v[a]["score"] <= 5 for a in AXES)
    return {a: v[a]["score"] for a in AXES} | {"diagnosis_match": v["diagnosis_matches_reference"]}


def judge(records, run_dir, workers=4):
    from openai import OpenAI

    model = os.environ["JUDGE_MODEL"]
    client = OpenAI(base_url=os.environ["JUDGE_BASE_URL"], api_key=os.environ["JUDGE_API_KEY"])
    cache_path = Path(run_dir) / "judge.jsonl"
    cache = {c["key"]: c["verdict"] for c in map(json.loads, cache_path.read_text().splitlines())} if cache_path.exists() else {}

    def one(r):
        p = prompt(r)
        key = hashlib.sha256(f"{model}\n{p}".encode()).hexdigest()[:16]
        if "error" not in cache.get(key, {"error": 1}):
            return r["case_id"], cache[key]
        try:
            resp = client.chat.completions.create(model=model, temperature=0, messages=[{"role": "user", "content": p}])
            verdict = parse(resp.choices[0].message.content)
        except Exception as e:
            verdict = {"error": f"{type(e).__name__}: {e}"[:300]}
        cache[key] = verdict
        return r["case_id"], verdict

    with ThreadPoolExecutor(workers) as ex:
        verdicts = dict(ex.map(one, records))
    cache_path.write_text("".join(json.dumps(dict(key=k, verdict=v)) + "\n" for k, v in cache.items()))
    return verdicts
