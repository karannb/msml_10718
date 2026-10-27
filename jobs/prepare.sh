#!/bin/bash
# Steps 0-3: check the test set rebuilds identically, list the pool, embed every image, inspect near-duplicates.
set -euo pipefail
$PY build_testset.py
git diff --stat --exit-code data/testset.csv
echo "testset.csv unchanged"
$PY build_pool.py
$PY embed.py
$PY clean.py --inspect
