"""Call a system under test and check its response against the contract in README.md."""

import base64
import importlib
import json
import mimetypes
import os
import time
from pathlib import Path

import pandas as pd
import requests

from harness.data import LABELS, native_labels


def make(spec, auth_env=None, timeout=120):
    if spec.startswith(("http://", "https://")):
        return HttpSystem(spec, auth_env, timeout)
    if spec.startswith("file:"):
        return FileSystem(spec[5:])
    if spec.startswith("py:"):
        module, _, fn = spec[3:].partition(":")
        return getattr(importlib.import_module(module), fn)
    raise ValueError(f"unknown spec {spec!r}: use https://..., file:<path> or py:<module>:<function>")


class HttpSystem:
    def __init__(self, url, auth_env, timeout, retries=2):
        self.url, self.timeout, self.retries = url, timeout, retries
        self.headers = {"Authorization": f"Bearer {os.environ[auth_env]}"} if auth_env else {}

    def __call__(self, case, diagnosis=None):
        image = dict(mime=mimetypes.guess_type(case["image"])[0] or "image/jpeg",
                     data_b64=base64.b64encode(Path(case["image"]).read_bytes()).decode())
        payload = dict(case_id=case["case_id"], description=case["description"], image=image, diagnosis=diagnosis)
        for attempt in range(self.retries + 1):
            try:
                r = requests.post(self.url, json=payload, headers=self.headers, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                status = getattr(e.response, "status_code", None)
                if attempt == self.retries or (status is not None and status < 500 and status != 429):
                    raise
                time.sleep(2 ** (attempt + 1))


class FileSystem:
    """JSONL records in the contract, or a CSV with image, pred[, confidence]; matched on case_id or image."""

    def __init__(self, path):
        if path.endswith(".csv"):
            records = [dict(image=r["image"], diagnosis={k: v for k, v in [("label", r["pred"]), ("confidence", r.get("confidence"))] if pd.notna(v)})
                       for r in pd.read_csv(path).to_dict("records")]
        else:
            records = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        self.key = "case_id" if all("case_id" in r for r in records) else "image"
        self.by_key = {r[self.key]: r for r in records}
        assert len(self.by_key) == len(records), f"{path}: duplicate {self.key}s"

    def __call__(self, case, diagnosis=None):
        return self.by_key[case[self.key]]


def check(resp):
    """Return (cleaned response, list of contract violations)."""
    out, problems = {}, []
    d = resp.get("diagnosis")
    if d is not None:
        if d.get("label") not in LABELS + native_labels():
            problems.append(f"diagnosis.label {d.get('label')!r} is not a broad or native label")
        elif d.get("confidence") is not None and not 0 <= float(d["confidence"]) <= 1:
            problems.append("diagnosis.confidence outside 0-1")
        else:
            out["diagnosis"] = {k: d[k] for k in ["label", "confidence"] if d.get(k) is not None}
    rem = resp.get("remedies")
    if rem is not None:
        if not isinstance(rem, list) or not all(isinstance(x, dict) and isinstance(x.get("action"), str) for x in rem):
            problems.append("remedies must be a list of {action, source_url}")
        else:
            out["remedies"] = [{"action": x["action"], "source_url": x.get("source_url")} for x in rem]
    out["usage"] = {k: v for k, v in (resp.get("usage") or {}).items() if k in ["cost_usd", "input_tokens", "output_tokens"]}
    return out, problems
