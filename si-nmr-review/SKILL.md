---
name: si-nmr-review
description: Pre-screen 1H NMR spectra from an organic-chemistry Supporting Information file against the Wang group spectral guidelines (2026-10-25) and suggest an E/V/S/N grade with reasons for each spectrum. Use when someone uploads SI spectrum images, a ZIP of them, or an SI PDF and asks to check, grade or pre-review the spectra. It produces suggestions for a human reviewer, never final grades.
---

# SI NMR pre-screen

The grade comes from fixed code and a fixed rule file, so the same spectrum always gets the same grade and the same reasons. Your only judgement-free job is to copy printed text off each page into a fixed form; the scripts do every measurement and apply every rule. Do not grade spectra yourself and do not change a grade the scripts give.

`SKILL_DIR` below means the folder that contains this SKILL.md.

## 1. Set up
- Inputs: on claude.ai the user's uploads are usually in `/mnt/user-data/uploads`; otherwise use the files the user names. Work in a scratch folder, e.g. `WORK=/tmp/si-nmr`.
- Outputs: write to `/mnt/user-data/outputs/si-nmr-review` if `/mnt/user-data/outputs` exists, else to `$WORK/out`.
- Check the libraries: `python -c "import numpy, scipy, PIL"`. If one is missing, `pip install numpy scipy pillow` (add `--break-system-packages` if pip asks for it). For PDFs, `pypdf` and `pypdfium2` (or `pymupdf`) are also needed.

## 2. Collect the spectra
```
python SKILL_DIR/scripts/prepare_inputs.py <uploads> --out $WORK/images
```
It takes images, ZIPs of images and PDFs (embedded screenshots are extracted; vector pages are rendered). Each image must hold one spectrum. If a rendered page holds two, crop it into two images with PIL before going on. Tell the user how many spectra were found.

## 3. Transcribe each image (the only step that is yours)
For every image `NAME.png`, write `$WORK/transcriptions/NAME.json` following `SKILL_DIR/schemas/transcription.schema.json`. Copy only what is printed; do not judge anything.
- `axis_labels`: every number printed under the main x-axis, left to right, exactly as printed. Leave out labels cut off by the image edge.
- `integral_values`: every integral value under the main spectrum, from highest ppm (left) to lowest. Integrals of an inset go in that inset's entry.
- `compound_number`, `frequency_text`, `solvent_text`: as printed, or "" if not printed. Do not infer them.
- `annotations`: labels such as "EtOAc", "S.M", "H2O" with the ppm they point to.
- `legibility`: good, fair (readable with effort) or poor (labels unreadable, e.g. a blurred scan).
Small text is easier to read on enlarged crops: `python SKILL_DIR/scripts/zoom.py $WORK/images/NAME.png $WORK/zoom` writes enlarged header, axis and integral strips (with the rotated integral values turned upright).
Then check yourself once: re-read the axis labels and integral values of every image from the enlarged crops and correct any value that differs. The integral count must equal the number of integral brackets drawn.

## 4. Run the pipeline
```
python SKILL_DIR/scripts/review_images.py $WORK/images $WORK/transcriptions <outputs> [--context <context_dir>]
```
Optional context (author facts, one `NAME.json` per spectrum): `ctx_high_complexity`, `ctx_small_sample`, `ctx_unstable`, `ctx_isomers_reported`, `ctx_low_purity_reason_stated` (true/false), `ctx_journal`. Ask the user for these only if they offer them; without context the grade is the strict one.

It writes `report.md` (summary table, whole-SI check, per-spectrum reasons and items that need a person), `summary.csv`, and for each spectrum `NAME_overlay.png` (what the code took as baseline, integrals and impurity signals), `NAME_features.json` and `NAME_grade.json`.

## 5. Report back
- Show the summary table from `report.md` and the whole-SI distribution.
- For each spectrum give the grade, the purity range and the main reasons as the report states them, and list the "Needs a person" items.
- Look at each overlay. If a structure, an inset or a label was taken as part of the spectrum, or an integral bracket is clearly missed, say that this spectrum's numbers are unreliable. Never patch numbers by hand.
- Offer the files in the output folder.
- Close with: these are suggestions from fixed rules; the final grade is the reviewer's.

## What is fixed where
- `scripts/nmrimage.py`: ppm calibration from the tick marks, trace extraction, integral brackets.
- `scripts/features.py`: signal finding; residual solvent, water, grease, common solvents (`config/solvent_shifts.json`) and 13C satellites; purity bounds; display fractions.
- `config/rubric.json`: thresholds and rules, written from the Wang group guidelines by agents that never saw the example grades. Change it only with the group leader's agreement, and keep the old version.
- `scripts/grade.py`: the fixed algorithm that applies the rubric.

## Limits
- Images are low resolution (about 0.01 ppm and 0.1-0.2% of display height per pixel). Shimming, linewidth and 13C signal-to-noise cannot be measured from them; those need the raw data.
- Purity is a range. The low bound counts each unknown signal as a separate 1-proton species, the high bound as 3 protons. Small impurity areas can be slightly underestimated.
- A line within 0.04 ppm of a known solvent shift is called that solvent, so a product line at the same place can be mistaken for it. Grease and hexanes are not told apart.
- When integral brackets cannot be read, regions are inferred from the value labels; a small line right next to a product multiplet can then be absorbed into the product.
- Spectra drawn in blue or green are not supported. Scanned or blurred pages, or axes whose labels do not match the transcription, are refused rather than guessed; such a spectrum is graded on page facts only.
- The solvent shift table was entered from memory of Gottlieb 1997 and Fulmer 2010 and must be checked against the papers.
- Tested on 13 raster 1H examples. The rubric as written is about 2.8 notches harsher than the group leader's own grades on those examples; treat grades as a screen, not a verdict.
