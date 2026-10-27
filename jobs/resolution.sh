#!/bin/bash
# Higher-resolution embeddings (448 x 448 instead of 224 x 224), same cleaned split, then both heads and the Reddit cases.
set -euo pipefail
F=$MSML_DATA/features
[ -f $F/dinov2-base.npz ] && mv $F/dinov2-base.npz $F/dinov2-base-224px.npz
$PY -c "from embed import processor; import numpy as np, PIL.Image as I; print('448 crop:', processor(448)(images=I.new('RGB', (640, 480)), return_tensors='pt').pixel_values.shape)"
$PY embed.py --image_size 448
$PY train_head.py --setting indoor --image_size 448
$PY train_head.py --setting all --image_size 448
$PY eval_reddit.py
