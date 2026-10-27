"""Enlarged crops that make small printed text easier to transcribe.

    python zoom.py <image> <out_dir> [--scale 3]

Writes <name>_top.png (header and peak-label row), <name>_bottom.png (integral values and
axis labels) and <name>_left.png (structure and caption area), each enlarged. Rotated
integral values are also written turned upright (<name>_bottom_rot.png).
"""
import argparse
import os

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=3.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    im = Image.open(a.image).convert("RGB")
    W, H = im.size
    name = os.path.splitext(os.path.basename(a.image))[0]
    crops = {
        "top": (0, 0, W, int(0.22 * H)),
        "bottom": (0, int(0.72 * H), W, H),
        "left": (0, 0, int(0.45 * W), int(0.75 * H)),
    }
    for key, box in crops.items():
        c = im.crop(box)
        c = c.resize((int(c.width * a.scale), int(c.height * a.scale)), Image.LANCZOS)
        c.save(os.path.join(a.out, f"{name}_{key}.png"))
        if key == "bottom":
            c.rotate(90, expand=True).save(os.path.join(a.out, f"{name}_bottom_rot.png"))
    print(os.path.join(a.out, name + "_*.png"))


if __name__ == "__main__":
    main()
