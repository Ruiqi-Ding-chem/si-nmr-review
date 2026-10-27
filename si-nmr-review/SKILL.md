---
name: si-nmr-review
description: Pre-screen the 1H NMR spectra of a Supporting Information file against a research group's written spectral standard and suggest an E/V/S/N grade with reasons. Use when someone asks to check, grade or pre-review SI spectra or spectrum images before group peer review. It produces suggestions for a human reviewer, never final grades.
---

# SI NMR pre-screen

The grade comes from fixed code and a fixed rubric, so the same spectrum always gets the same grade and the same reasons. The model only does one thing: copy printed text off each page into a fixed form.

## Inputs
- One image per spectrum page (PNG or JPEG), cropped to the spectrum. A PDF page can be rendered to an image first.
- Optional context per spectrum, from the author's compound list (`ctx_high_complexity`, `ctx_small_sample`, `ctx_unstable`, `ctx_isomers_reported`, `ctx_low_purity_reason_stated`, `ctx_journal`, `ctx_journal_requires_freq_solvent`). Without context the grade is the strict one.

## Steps
1. **Transcribe each image** into `schemas/transcription.schema.json`. Copy only what is printed: axis labels left to right, integral values from highest ppm, compound number, frequency, solvent, structure present, annotations such as "EtOAc" or "S.M", insets. Do not judge anything. Have two independent transcriptions made; where they disagree on the axis labels, the integral values or the printed text, look again and settle it. Save as `<image name>.json`.
2. **Run the pipeline**:
   ```
   python scripts/review_images.py <images_dir> <transcriptions_dir> <out_dir> [--context <context_dir>]
   ```
   For every image it writes `_features.json` (what was measured), `_grade.json` (rules that fired), and `_overlay.png` (what the code took as baseline, integrals and impurity signals). For the whole set it writes `report.md` and `summary.csv`.
3. **Check the overlays** before trusting a grade. If a structure, inset or label was read as part of the spectrum, or an integral bracket was missed, the features for that spectrum are wrong. Report it; do not patch the numbers by hand.
4. **Hand the report to the human reviewers.** Lead with the items under "Needs a person" and with spectra whose low- and high-purity grades differ.

## What is fixed where
- `scripts/nmrimage.py`: pixel to ppm calibration from the tick marks, trace extraction, integral brackets.
- `scripts/features.py`: signal finding, solvent/water/grease/13C-satellite assignment from `config/solvent_shifts.json`, purity bounds, display fractions.
- `config/rubric.json`: thresholds and rules, written from your group's standard (not included in this repository; `config/rubric.example.json` shows the format). Change it only with the group leader's agreement, and keep the old version.
- `scripts/grade.py`: the fixed algorithm that applies the rubric.

## Limits
- Images are low resolution (about 0.01 ppm and 1-2% of display height per pixel). Shimming, linewidth and 13C signal-to-noise cannot be measured from them; those need the raw Bruker data.
- Purity is a range. The low bound counts each unknown signal as a separate 1-proton species; the high bound as 3 protons. Integrals are assumed to count protons per molecule, which halves impurity mol% for C2-symmetric compounds integrated per half.
- A line within 0.04 ppm of a known solvent shift is assigned to that solvent, so a product line at the same place can be mistaken for it. Grease and hexanes are not told apart.
- Scanned or blurred pages may fail calibration; then only the page facts are graded and the report says so.
- The solvent shift table was entered from memory of Gottlieb 1997 and Fulmer 2010; check it against the papers.
- When the integral brackets cannot be read, the regions are inferred from the value labels; a small line right next to a product multiplet can then be absorbed into the product.
- Small impurity areas are measured above a local baseline and can be slightly underestimated.
- Spectra drawn in blue or green are not supported (those colours are removed as labels and integrals).
- An axis whose label count does not match the transcription, or has an extra word at one end, is refused rather than guessed; the spectrum is then graded on page facts only.
- So far tested privately on 13 raster 1H examples only.
