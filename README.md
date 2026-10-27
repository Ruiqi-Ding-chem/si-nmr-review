# si-nmr-review

A Claude skill that pre-screens the 1H NMR spectra of an organic-chemistry Supporting Information (SI) file against the Wang group spectral guidelines (University of Pittsburgh, 2026-10-25). For each spectrum it measures purity, impurities and presentation with fixed code, applies a rule file, and suggests an E/V/S/N grade with reasons for a human reviewer. It never gives final grades.

Status: prototype (v0.1), tested on the 13 published example spectra in `examples/`.

## Use it on claude.ai (no installation)

1. Download **[si-nmr-review.zip](https://github.com/1e32e3e/si-nmr-review/releases/latest/download/si-nmr-review.zip)** from the latest release. Use this file, not GitHub's "Download ZIP" button (that adds an extra folder level, and claude.ai refuses it).
2. On claude.ai: **Settings > Capabilities**, turn on code execution ("Create and edit files").
3. **Customize > Skills > + > Create skill > Upload a skill**, choose `si-nmr-review.zip`, and make sure the skill is switched on.
4. Start a new chat, upload the spectra (images, a ZIP of images, or an SI PDF; at most 20 files per chat) and write, for example: *Use si-nmr-review to pre-screen these 1H spectra.*
5. Claude copies the printed labels, runs the scripts and returns a report with a grade, purity range and reasons per spectrum, plus overlay images showing what was measured. To try the lenient rule set, add: *use config/rubric.relaxed.json*.

To try it without your own data, download [example-spectra.zip](https://github.com/1e32e3e/si-nmr-review/releases/latest/download/example-spectra.zip) (the 13 examples) and upload it in step 4.

## Use it locally

Python 3.9+ with numpy, scipy and Pillow (`pip install -r requirements.txt`). The examples come with ready transcriptions, so no model is needed:

```
python si-nmr-review/scripts/review_images.py examples/images examples/transcriptions out
```

With your own spectra: `scripts/prepare_inputs.py` collects images from a folder, ZIP or PDF; then write one transcription JSON per image (see `schemas/transcription.schema.json`), by hand or with Claude Code following `SKILL.md`.

## How it works

```
spectrum image ──► 1. transcription (model) ──► 2. digitize ──► 3. measure ──► 4. grade (rubric) ──► report + overlays
                      copies printed text only      fixed code       fixed code      fixed code
```

| File | Job |
|---|---|
| `SKILL.md` | Instructions for the model: where the files are, how to transcribe, what to run, how to report |
| `scripts/prepare_inputs.py` | Images from uploads, ZIPs and PDFs |
| `scripts/zoom.py` | Enlarged crops to help read small labels |
| `scripts/nmrimage.py` | ppm calibration from tick marks, trace extraction, integral brackets |
| `scripts/features.py` | Signals; residual solvent, water, grease, common solvents, 13C satellites; purity range; peak heights |
| `scripts/grade.py` | Applies a rubric with a fixed algorithm |
| `scripts/review_images.py` | Runs steps 2-4 for a folder and writes the report |
| `config/rubric.json` | The rules, written from the guidelines by agents that never saw the example grades |
| `config/rubric.relaxed.json` | Same rules with five open decisions taken the lenient way (not approved; for comparison) |
| `config/solvent_shifts.json` | Residual solvent, water, grease and common-solvent shifts |

## Results on the 13 examples

Against the group leader's own grades: the strict rubric is about 2.8 notches harsher on average (4 of 13 within one notch); the relaxed rubric matches 3 exactly and 5 within one notch. Both agree with him on the clearly failing spectra. The remaining differences come from context he applies (complex products, very small samples) and from what a screenshot cannot show (shimming, whether a mixture is reported in the text).

## Limits

See the Limits section of `si-nmr-review/SKILL.md`. In short: raster images limit precision; shimming and 13C signal-to-noise need raw data; purity is a range; the solvent shift table must be checked against Fulmer et al., Organometallics 2010, 29, 2176.

## Related tools

A search on 2026-10-27 found no existing tool that reviews the NMR spectra of an organic-chemistry SI against quality and presentation standards end to end. Tools that do related jobs:

- Impurity and solvent shifts: Gottlieb et al. 1997, Fulmer et al. 2010, Babij et al. 2016; [NMR-1H-Analysis](https://github.com/Dopamine-tech/NMR-1H-Analysis) (spectrum-to-structure assignment) ships an MIT impurity table.
- Purity without an internal standard: the relative "100%" qHNMR method of Pauli et al., J. Med. Chem. 2014, 57, 9220.
- Vector-PDF figures: [pdf2plot](https://github.com/adamkucharski/pdf2plot) reads traces from PDF paths instead of pixels.
- Raw data: [nmrglue](https://github.com/jjhelmus/nmrglue), [OpenReadout](https://github.com/openreadout/openreadout) (local MCP/CLI, noise and S/N).
- Raw-data quality and structure checks (commercial): Mnova Gears SQA, Mnova GSD peak classification, Mnova Verify.
- Other parts of an SI review: [HRMS-Checker 2.0](https://github.com/match22lab/HRMS-Checker-2.0), the Chemotion (Semi-)Automatic Review Process, DECIMER for structures in images.

## Planned

- Read vector PDFs directly (trace and text from the PDF, no transcription step).
- Read Bruker raw data (nmrglue): exact ppm axis, solvent and frequency from the parameters, 13C signal-to-noise.
- Join other checks (HRMS, 13C/structure, text vs spectrum) into a full SI review.

## License

MIT. The example spectra are from published work and are included for testing only.
