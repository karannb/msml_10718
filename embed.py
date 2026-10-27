"""Step 2: compute the frozen DINOv2 image embedding of every image in data/pool.csv and data/testset.csv.

    python embed.py --image_size 224   # shorter side resized to 256, center crop 224 x 224 (DINOv2's default)
    python embed.py --image_size 448   # same, scaled by 2: shorter side 512, center crop 448 x 448

Writes $MSML_DATA/features/dinov2-base-<size>px.npz with `image` (paths), `feat` (N x 1536) and `md5` (file hash).
"""

import argparse
import hashlib
import os

import nb
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModel

MODEL = "facebook/dinov2-base"  # ViT-B/14, 86M parameters, kept frozen


def features_path(size):
    return os.path.join(os.environ.get("MSML_DATA", "."), "features", f"dinov2-base-{size}px.npz")


def processor(size):
    """Resize the shorter side to size * 256 / 224, center crop size x size, normalize with ImageNet mean / std."""
    return AutoImageProcessor.from_pretrained(MODEL, size={"shortest_edge": size * 256 // 224},
                                              crop_size={"height": size, "width": size})


def load(path, proc):
    """Opens an image the way a phone shows it (exif_transpose applies the rotation flag), as RGB pixels for DINOv2."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return proc(images=img, return_tensors="pt").pixel_values[0]


@nb.core
@torch.no_grad()
def embed(model, pixels):
    """Image embedding = [CLS token ; mean of the patch tokens] of the last layer (the DINOv2 paper's linear-probe input)."""
    h = model(pixel_values=pixels).last_hidden_state  # (B, 1 + patches, 768)
    return torch.cat([h[:, 0], h[:, 1:].mean(1)], dim=1)  # (B, 1536)


class Files(torch.utils.data.Dataset):
    def __init__(self, paths, proc):
        self.paths, self.proc = paths, proc

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        p = self.paths[i]
        md5 = hashlib.md5(open(p, "rb").read()).hexdigest()
        try:
            return p, md5, load(p, self.proc)
        except Exception:  # unreadable or truncated file
            return p, md5, None


def collate(batch):
    ok = [b for b in batch if b[2] is not None]
    bad = [b[0] for b in batch if b[2] is None]
    return [b[0] for b in ok], [b[1] for b in ok], torch.stack([b[2] for b in ok]), bad


def main(size):
    out = features_path(size)
    paths = sorted(set(pd.read_csv("data/pool.csv").image) | set(pd.read_csv("data/testset.csv").image))
    model = AutoModel.from_pretrained(MODEL).cuda().eval()
    loader = torch.utils.data.DataLoader(Files(paths, processor(size)), batch_size=128, collate_fn=collate,
                                         num_workers=int(os.environ.get("OMP_NUM_THREADS", 4)))
    done, md5s, feats, bad = [], [], [], []
    for i, (p, m, x, b) in enumerate(loader):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            feats.append(embed(model, x.cuda()).float().cpu().numpy())
        done += p
        md5s += m
        bad += b
        if i % 20 == 0:
            print(f"{len(done)}/{len(paths)}", flush=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez(out, image=np.array(done), feat=np.concatenate(feats), md5=np.array(md5s), unreadable=np.array(bad))
    print(f"wrote {out}: {len(done)} images, {len(bad)} unreadable: {bad}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--image_size", type=int, default=224)
    main(p.parse_args().image_size)
