"""Run a system over the test images and save its outputs to runs/<run>/.

    python run_system.py --system SPEC --run NAME
    python run_system.py --classifier SPEC [--recommender SPEC] --run NAME

SPEC: https://... (endpoint), file:<outputs.jsonl|.csv> or py:<module>:<function>. Re-running a run retries failed cases.
"""

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from harness import adapters
from harness.data import cases


def call(system, case, diagnosis=None):
    start = time.perf_counter()
    try:
        out, problems = adapters.check(system(case, diagnosis))
        stage = dict(latency_ms=round((time.perf_counter() - start) * 1000, 1), **out.pop("usage"))
        if problems:
            stage["error"] = "contract: " + "; ".join(problems)
        return out, stage
    except Exception as e:
        return {}, dict(latency_ms=round((time.perf_counter() - start) * 1000, 1), error=f"{type(e).__name__}: {e}"[:500])


def run_case(case, systems):
    rec = dict(case_id=case["case_id"], image=case["image"], stages={})
    if "system" in systems:
        out, rec["stages"]["system"] = call(systems["system"], case)
        return rec | out
    out, rec["stages"]["classifier"] = call(systems["classifier"], case)
    rec |= out
    if "recommender" in systems and "diagnosis" in rec:
        out, rec["stages"]["recommender"] = call(systems["recommender"], case, rec["diagnosis"])
        rec["remedies"] = out.get("remedies")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--system")
    ap.add_argument("--classifier")
    ap.add_argument("--recommender")
    ap.add_argument("--auth-env", help="env var holding a bearer token for https:// endpoints")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    load_dotenv()
    assert bool(args.system) != bool(args.classifier), "use --system, or --classifier [--recommender]"

    specs = {k: getattr(args, k) for k in ["system", "classifier", "recommender"] if getattr(args, k)}
    out_dir = Path("runs") / args.run
    out_dir.mkdir(parents=True, exist_ok=True)
    meta, outputs = out_dir / "meta.json", out_dir / "outputs.jsonl"
    if meta.exists():
        assert json.loads(meta.read_text())["specs"] == specs, f"{meta} has different systems; use a new --run name"
    meta.write_text(json.dumps(dict(run=args.run, specs=specs), indent=2) + "\n")

    done = {}
    if outputs.exists():
        done = {r["case_id"]: r for r in map(json.loads, outputs.read_text().splitlines())
                if not any("error" in s for s in r["stages"].values())}
    todo = [c for c in cases() if c["case_id"] not in done]
    systems = {k: adapters.make(v, args.auth_env) for k, v in specs.items()}

    lock = threading.Lock()
    with outputs.open("w") as f:
        for r in done.values():
            f.write(json.dumps(r) + "\n")

        def work(case):
            r = run_case(case, systems)
            with lock:
                f.write(json.dumps(r) + "\n")
                f.flush()

        with ThreadPoolExecutor(args.workers) as ex:
            list(ex.map(work, todo))
    print(f"{args.run}: ran {len(todo)}, reused {len(done)} -> {outputs}")


if __name__ == "__main__":
    main()
