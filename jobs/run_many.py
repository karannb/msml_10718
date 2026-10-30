"""Run several eval_resolved.py configurations in one process (the login node allows few threads per user).

    python jobs/run_many.py "--prompt guided-v2 --threads dev" "--prompt guided-v2+kb --threads dev --search" ...
"""
import os
import shlex
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import eval_resolved  # noqa: E402


def run(argv):
    try:
        eval_resolved.main(shlex.split(argv))
        return f"done: {argv}"
    except Exception:
        return f"FAILED: {argv}\n{traceback.format_exc()}"


with ThreadPoolExecutor(len(sys.argv) - 1) as pool:
    for msg in pool.map(run, sys.argv[1:]):
        print(msg, flush=True)
