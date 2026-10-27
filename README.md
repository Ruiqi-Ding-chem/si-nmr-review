# si-nmr-review

A prototype that pre-screens the 1H NMR spectra in an organic-chemistry Supporting Information (SI) file against a research group's written spectral standard. For each spectrum it measures purity, impurities and presentation, applies a rule file, and suggests a grade with reasons for a human reviewer. It never gives final grades.

Status: early prototype, tested privately on 13 raster examples. The rule file used in that test belongs to the group whose standard it encodes and is not included here.

## How it works

```
spectrum image ──► 1. transcription (model or person) ──► 2. digitize (code) ──► 3. measure (code) ──► 4. grade (code + rubric) ──► report + overlays
```

1. **Transcription.** The only step that needs a model: copy what is printed on the page (axis labels, integral values, compound number, frequency, solvent, annotations) into `schemas/transcription.schema.json`. Nothing is judged here. `SKILL.md` tells an agent (for example Claude Code) to do it twice and reconcile; a person can also type it.
2. **Digitize** (`scripts/nmrimage.py`). Calibrates ppm from the axis tick marks, extracts the trace, finds the integral brackets.
3. **Measure** (`scripts/features.py`). Finds signals, assigns residual solvent, water, grease, common solvents (`config/solvent_shifts.json`) and 13C satellites, estimates purity as a range, measures peak heights against the display.
4. **Grade** (`scripts/grade.py`). Applies `config/rubric.json` with a fixed algorithm: base grade from purity, deductions per rule group, caps, optional author context.

`scripts/review_images.py` runs steps 2-4 for a folder and writes `report.md`, `summary.csv`, and an overlay per spectrum showing what the code measured.

## Use

Requires Python 3.9+ with numpy, scipy and Pillow (`pip install -r requirements.txt`).

```
python si-nmr-review/scripts/review_images.py <images_dir> <transcriptions_dir> <out_dir> [--context <context_dir>] [--rubric <rubric.json>]
```

For each image `NAME.png` there must be `NAME.json` in the transcriptions folder. Without `config/rubric.json` the example rubric is used.

As a Claude skill, the `si-nmr-review/` folder is the skill: `SKILL.md` plus scripts and config.

## Rubric format

A rubric is JSON: `base_grade_table` (purity to grade), `rules` (condition on measured features; effect deduct, cap or flag; the sentence of the standard it implements), `group_max_deduction`, `context_modifiers`, and lists of items a person must check. `config/rubric.example.json` shows the format; the feature names are those written by `features.py`.

## Limits

See the Limits section of `si-nmr-review/SKILL.md`. In short: raster images limit precision; shimming and 13C signal-to-noise need raw data; purity is a range; the solvent shift table must be checked against Fulmer et al., Organometallics 2010, 29, 2176 before use.

## Related tools

A search on 2026-10-27 found no existing tool that reviews the NMR spectra of an organic-chemistry SI against quality and presentation standards end to end. Parts of the job are covered elsewhere:

- Impurity and solvent shifts: Gottlieb et al. 1997, Fulmer et al. 2010, Babij et al. 2016; [NMR-1H-Analysis](https://github.com/Dopamine-tech/NMR-1H-Analysis) ships an MIT impurity table.
- Purity without an internal standard: the relative "100%" qHNMR method of Pauli et al., J. Med. Chem. 2014, 57, 9220.
- Vector-PDF figures: [pdf2plot](https://github.com/adamkucharski/pdf2plot) reads traces from PDF paths instead of pixels.
- Raw data: [nmrglue](https://github.com/jjhelmus/nmrglue), [OpenReadout](https://github.com/openreadout/openreadout) (local MCP/CLI, noise and S/N).
- Raw-data quality and structure checks (commercial): Mnova Gears SQA, Mnova GSD peak classification, Mnova Verify.
- Other parts of an SI review: [HRMS-Checker 2.0](https://github.com/match22lab/HRMS-Checker-2.0), the Chemotion (Semi-)Automatic Review Process, DECIMER for structures in images.

## Planned

- Read vector PDFs directly (trace and text from the PDF, no transcription step).
- Read Bruker raw data (nmrglue): exact ppm axis, solvent and frequency from the parameters, 13C signal-to-noise.
