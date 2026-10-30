import json
from functools import cache
from pathlib import Path

import pandas as pd

LABELS = ["healthy", "watering", "fungal_bacterial", "pest", "other"]
QUESTION = "What's wrong with my plant?"


@cache
def test_set():
    # The classification eval is the 100 Indoor images in data/testset.csv.
    return pd.read_csv("data/testset.csv").query("source == 'indoor'").reset_index(drop=True)


@cache
def native_labels():
    return sorted(test_set().orig_label.unique())  # the 16 plant + condition classes


def cases():
    return [dict(case_id=f"{i:03d}", image=img, description=QUESTION) for i, img in enumerate(test_set().image)]


@cache
def gold():
    return json.loads(Path("data/gold_advice.json").read_text())


@cache
def corpus():
    return pd.read_csv("data/corpus_sources.csv")
