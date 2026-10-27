"""Classify phone photos with a trained head:  python predict.py results/all-224px/head.npz photo1.jpg [photo2.jpg ...]"""

import sys

import numpy as np
import torch
from transformers import AutoModel

from embed import MODEL, embed, load, processor


def probabilities(head_path, photos):
    """Returns the labels and an (images x labels) array of softmax probabilities."""
    head = np.load(head_path, allow_pickle=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModel.from_pretrained(MODEL).to(device).eval()
    proc = processor(int(head["image_size"]) if "image_size" in head else 224)
    z = embed(model, torch.stack([load(p, proc) for p in photos]).to(device)).float().cpu().numpy()
    logits = ((z - head["mu"]) / head["sd"]) @ head["W"].T + head["b"]
    prob = np.exp(logits - logits.max(1, keepdims=True))
    return head["labels"], prob / prob.sum(1, keepdims=True)


def main(head_path, photos):
    labels, prob = probabilities(head_path, photos)
    for p, row in zip(photos, prob):
        order = np.argsort(-row)
        print(p, "->", ", ".join(f"{labels[k]} {row[k]:.0%}" for k in order[:3]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
