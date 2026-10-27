"""Grade a folder of 1H spectrum images with the fixed pipeline.

    python review_images.py <images_dir> <transcriptions_dir> <out_dir> [--context <context_dir>] [--rubric <rubric.json>]

For each image NAME.png/.jpeg there must be a transcription <transcriptions_dir>/NAME.json
(schema: schemas/transcription.schema.json). An optional <context_dir>/NAME.json holds
author-supplied ctx_* facts. Writes per spectrum: NAME_features.json, NAME_grade.json,
NAME_overlay.png; and report.md + summary.csv for the whole set.
"""
import argparse
import csv
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nmrimage  # noqa: E402
import features as feat  # noqa: E402
import grade as gr  # noqa: E402

COLORS = {"unknown": (230, 0, 0), "common_solvent": (255, 140, 0), "water": (0, 90, 255),
          "grease": (150, 0, 200), "silicone_grease": (150, 0, 200), "residual_solvent": (0, 160, 0),
          "c13_satellite": (140, 140, 140), "starting_material": (140, 70, 0)}


def overlay(path, dig, segs, out):
    im = Image.open(path).convert("RGB")
    dr = ImageDraw.Draw(im)
    xl = dig["x_left"]
    for i, x in enumerate(range(xl, dig["x_right"] + 1)):
        dr.point((x, dig["base"][i]), fill=(255, 0, 255))
    for r0, r1 in dig["regions_px"]:
        y = dig["axis_y"] - 6
        dr.line([(r0, y), (r1, y)], fill=(255, 128, 0), width=2)
    for sg in segs:
        c = COLORS.get(sg.get("cls"))
        if not c:
            continue
        x0, x1 = xl + sg["s"], xl + sg["e"]
        ytop = dig["base"][sg["apex"]] - sg.get("h_abs", sg["h"]) - dig["line_thickness_px"] - 3
        dr.rectangle([x0 - 1, ytop, x1, dig["base"][sg["apex"]] + 2], outline=c)
        dr.text((x0, max(0, ytop - 12)), f"{sg['ppm']:.2f}", fill=c)
    im.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images")
    ap.add_argument("transcriptions")
    ap.add_argument("out")
    ap.add_argument("--context")
    ap.add_argument("--rubric", default=None, help="rubric JSON (default: config/rubric.json, else config/rubric.example.json)")
    a = ap.parse_args()
    if a.rubric is None:
        a.rubric = os.path.join(HERE, "..", "config", "rubric.json")
        if not os.path.exists(a.rubric):
            a.rubric = os.path.join(HERE, "..", "config", "rubric.example.json")
            print("config/rubric.json not found; using the example rubric", file=sys.stderr)
    os.makedirs(a.out, exist_ok=True)
    with open(a.rubric, encoding="utf-8") as f:
        rubric = json.load(f)

    rows = []
    for path in sorted(glob.glob(os.path.join(a.images, "*"))):
        if os.path.splitext(path)[1].lower() not in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        tpath = os.path.join(a.transcriptions, name + ".json")
        if not os.path.exists(tpath):
            continue
        with open(tpath, encoding="utf-8") as f:
            ext = json.load(f)
        ctx = None
        if a.context and os.path.exists(os.path.join(a.context, name + ".json")):
            with open(os.path.join(a.context, name + ".json"), encoding="utf-8") as f:
                ctx = json.load(f)
        dig = None
        try:
            dig = nmrimage.digitize(path, ext["axis_labels"], n_integrals=len(ext.get("integral_values") or []) or None)
            f_, ev, segs = feat.compute(dig, ext, ctx)
        except Exception as e:  # the trace cannot be read: grade the page facts only and say so
            f_, ev = feat.presentation_only(ext, ctx, str(e))
            segs = []
        g = gr.grade_with_range(f_, rubric)
        with open(os.path.join(a.out, name + "_features.json"), "w", encoding="utf-8") as f:
            json.dump({"features": f_, "evidence": ev}, f, indent=1, ensure_ascii=False, default=float)
        with open(os.path.join(a.out, name + "_grade.json"), "w", encoding="utf-8") as f:
            json.dump(g, f, indent=1, ensure_ascii=False, default=float)
        if dig is not None:
            overlay(path, dig, segs, os.path.join(a.out, name + "_overlay.png"))
        rows.append({"name": name, "features": f_, "evidence": ev, "grade": g})

    write_report(rows, a.out, rubric)


def write_report(rows, out, rubric):
    ok = [r for r in rows if "grade" in r]
    with open(os.path.join(out, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["spectrum", "grade", "grade_if_purity_low", "grade_if_purity_high", "purity_low", "purity_high",
                    "tallest_class", "tallest_product_frac", "unknown_h_equiv", "grease_h_equiv", "rules_fired", "human_review"])
        for r in ok:
            g, f_ = r["grade"], r["features"]
            w.writerow([r["name"], g["grade"], g.get("grade_if_purity_low"), g.get("grade_if_purity_high"),
                        f_["purity_mol_pct_low"], f_["purity_mol_pct_high"], f_["tallest_peak_class"],
                        f_["tallest_product_peak_fraction"], f_["unknown_h_equiv"], f_["grease_h_equiv"],
                        "; ".join(x["id"] for x in g["fired"]), len(g["human_review"])])

    lines = ["# SI spectrum pre-screen", "",
             "Grades come from fixed rules (config/rubric.json) applied to measured features. "
             "They are suggestions for a human reviewer, not final grades.", ""]
    lines += ["| Spectrum | Grade | If purity low / high | Purity (mol%) | Main reasons |", "|---|---|---|---|---|"]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['name']} | error | | | {r['error']} |")
            continue
        g, f_ = r["grade"], r["features"]
        main = [x for x in g["fired"] if x["effect"] != "flag"][:3]
        pur = "n/a" if f_["purity_mol_pct_low"] is None else f"{f_['purity_mol_pct_low']:.0f}-{f_['purity_mol_pct_high']:.0f}"
        lines.append(f"| {r['name']} | {g['grade']} | {g.get('grade_if_purity_low', '')} / {g.get('grade_if_purity_high', '')} | {pur} | "
                     + "; ".join(x["title"] for x in main) + " |")
    counts = {s: 0 for s in gr.SCALE}
    for r in ok:
        counts[r["grade"]["grade"]] += 1
    n = len(ok)
    if n:
        s_band = sum(counts[k] for k in ("S-", "S", "S+"))
        bad = counts["S-"] + counts["N"]
        ve = n - s_band - counts["N"]
        lines += ["", "## Whole-SI check", "",
                  "Distribution: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v), "",
                  f"- V or E: {ve}/{n} ({100 * ve / n:.0f}%); the standard hopes for most spectra here.",
                  f"- S band: {s_band}/{n} ({100 * s_band / n:.0f}%); the standard allows 15-20%.",
                  f"- S- or N: {bad}; the standard allows none."]
    for r in ok:
        g, f_, ev = r["grade"], r["features"], r["evidence"]
        lines += ["", f"## {r['name']}: {g['grade']}", ""]
        if ev.get("digitization_error"):
            lines += [f"The trace could not be digitized ({ev['digitization_error']}); only page facts were graded.", ""]
        lines += [
                  f"Base grade from purity {g['base_grade']} (purity used {fmt(g['purity_used'])} mol%, basis {g['purity_basis']}); "
                  f"deductions {g['total_deduction']:g}; caps {', '.join(g['caps']) or 'none'}. "
                  f"Solvent {ev['solvent']} ({ev['solvent_source']}).", ""]
        for x in g["fired"]:
            tag = {"deduct": f"-{x.get('notches', 0):g}", "cap": f"cap {x.get('cap')}", "flag": "flag"}[x["effect"]]
            lines.append(f"- [{tag}] {x['title']}: {x['reason']}")
        for x in g["context"]:
            lines.append(f"- [context {x['effect']}] {x['note']}")
        if g["human_review"]:
            lines += ["", "Needs a person:"] + [f"- {h}" for h in g["human_review"]]
        sig = [s for s in ev["signals"] if s["class"] not in ("c13_satellite",)]
        if sig:
            lines += ["", "Signals outside the integrals: " + ", ".join(
                f"{s['ppm']:.2f} {s['class'].replace('_', ' ')}" + (f" ({s['solvent']})" if s.get("solvent") else "")
                + (f" {s['h_equiv']:.2f} H-eq" if s.get("h_equiv") is not None else "") for s in sig)]
        if g["rubric_errors"]:
            lines += ["", "Rubric errors: " + "; ".join(g["rubric_errors"])]
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def fmt(x):
    return "n/a" if x is None else f"{x:.1f}"


if __name__ == "__main__":
    main()
