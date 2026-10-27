#!/bin/bash
# Steps 3-4: clean and split the pool, then train the head in both settings.
set -euo pipefail
$PY clean.py
$PY train_head.py --setting indoor
$PY train_head.py --setting all
