# Sourced by every job. Images and features live on /data/user_data (compute nodes only); code and small results in home.
export MSML_DATA=/data/user_data/mdrieux/msml_10718
export HF_HOME=$MSML_DATA/hf
export PY=/home/mdrieux/msml_10718/.venv/bin/python
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-4}
