#!/bin/bash
#SBATCH -p preempt --qos=preempt_qos --gres=gpu:1 -c 8 --mem=48G --time=02:00:00
#SBATCH -J msml -o logs/%x-%j.out
# Runs the given command line on one GPU node:  sbatch -J name jobs/run.sbatch <command ...>
cd /home/mdrieux/msml_10718
source jobs/env.sh
echo "host=$(hostname) gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | paste -sd,) job=$SLURM_JOB_ID"
eval "$@"; status=$?
echo "EXIT=$status"; exit $status
