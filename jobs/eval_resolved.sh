#!/bin/bash
# Runs eval_resolved.py once, from whichever copy of the "resolved" job starts first (one is submitted per partition).
L=results/llm/.lock-resolved
if mkdir $L 2>/dev/null; then echo $SLURM_JOB_ID > $L/job
elif [ "$(cat $L/job)" != "$SLURM_JOB_ID" ]; then echo "another copy ($(cat $L/job)) is running; exiting"; exit 0; fi
scancel -u $USER -n resolved -t PENDING   # the other copy, still queued
$PY eval_resolved.py "$@"; s=$?
rm -rf $L; exit $s
