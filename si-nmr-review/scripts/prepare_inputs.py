"""Collect spectrum images from whatever the user uploaded.

    python prepare_inputs.py <input_dir_or_file> [<more> ...] --out <images_dir>

Accepts PNG/JPEG/TIFF/BMP images, ZIP archives of them, and PDF files. From a PDF it first
takes the embedded raster images (screenshots pasted into an SI); if a page has none, it
renders the page at 200 dpi. Writes every image to <images_dir> with a clean name and prints
the list. The digitizer works on one spectrum per image, so a rendered page that holds two
spectra must be cropped before transcription.
"""
import argparse
import io
import os
import re
import sys
import zipfile

from PIL import Image

IMG_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


def clean(name):
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.splitext(os.path.basename(name))[0]).strip("_")
    return base or "image"


def save(img, out, stem, written):
    stem = clean(stem)
    name, k = stem, 2
    while name in written:
        name, k = f"{stem}_{k}", k + 1
    path = os.path.join(out, name + ".png")
    img.convert("RGB").save(path)
    written[name] = path


def from_pdf(data, stem, out, written):
    images_found = 0
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        for p, page in enumerate(reader.pages, 1):
            for j, im in enumerate(page.images, 1):
                try:
                    pil = Image.open(io.BytesIO(im.data))
                except Exception:
                    continue
                if min(pil.size) < 150:        # logos, icons
                    continue
                save(pil, out, f"{stem}_p{p:02d}_img{j}", written)
                images_found += 1
    except ImportError:
        pass
    if images_found:
        return
    # no embedded rasters (vector PDF): render each page
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        for p in range(len(pdf)):
            save(pdf[p].render(scale=200 / 72).to_pil(), out, f"{stem}_p{p + 1:02d}", written)
        return
    except ImportError:
        pass
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        for p, page in enumerate(doc, 1):
            pix = page.get_pixmap(dpi=200)
            save(Image.open(io.BytesIO(pix.tobytes("png"))), out, f"{stem}_p{p:02d}", written)
        return
    except ImportError:
        print(f"cannot render {stem}.pdf: install pypdf, pypdfium2 or pymupdf", file=sys.stderr)


def handle(name, data, out, written):
    ext = os.path.splitext(name)[1].lower()
    if ext in IMG_EXT:
        try:
            save(Image.open(io.BytesIO(data)), out, name, written)
        except Exception as e:
            print(f"skipped {name}: {e}", file=sys.stderr)
    elif ext == ".pdf":
        from_pdf(data, clean(name), out, written)
    elif ext == ".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir() or "__MACOSX" in info.filename:
                    continue
                handle(info.filename, z.read(info), out, written)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    written = {}
    for inp in a.inputs:
        paths = [inp] if os.path.isfile(inp) else [os.path.join(inp, f) for f in sorted(os.listdir(inp))]
        for p in paths:
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    handle(os.path.basename(p), f.read(), a.out, written)
    for name, path in written.items():
        print(path)
    print(f"{len(written)} image(s) in {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
