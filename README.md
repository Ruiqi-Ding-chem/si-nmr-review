# si-nmr-review

A Claude skill that pre-screens the 1H NMR spectra of an organic-chemistry Supporting Information (SI) file against the Wang group spectral guidelines (University of Pittsburgh, 2026-10-25). For each spectrum it measures purity, impurities and presentation with fixed code, applies a rule file, and suggests an E/V/S/N grade with reasons for a human reviewer. It never gives final grades.

Status: prototype (v0.1), tested on the 13 published example spectra in `examples/`.

## Three ways to use it

| | Where | What runs | Repeatable |
|---|---|---|---|
| 1 | claude.ai without code execution (for example a university account where it is switched off) | Claude follows the written rules in `REVIEW_GUIDE.md` by looking at the spectra | no |
| 2 | claude.ai with code execution | the skill: scripts measure and grade | yes |
| 3 | your computer: Claude Code, or plain Python | the same skill and scripts | yes |

### 1. claude.ai, no code: the review guide

1. Create a Project and add [REVIEW_GUIDE.md](REVIEW_GUIDE.md) to its files. Optionally paste into the Project instructions: *Review NMR spectra by following REVIEW_GUIDE.md.*
2. In a chat in that Project, upload the spectra (images or the SI PDF) and ask: *Review these 1H spectra following the guide.*

On an account that allows skills, the same text is also a skill without scripts: `si-nmr-review-guide.zip` in the release.

### 2. claude.ai with code execution: the skill

1. Download **[si-nmr-review.zip](https://github.com/1e32e3e/si-nmr-review/releases/latest/download/si-nmr-review.zip)** from the latest release. Use this file, not GitHub's "Download ZIP" button (that adds an extra folder level, and claude.ai refuses it).
2. **Settings > Capabilities**: turn on code execution ("Create and edit files"). If there is no such setting, your organization has switched it off; use way 1 or 3.
3. **Customize > Skills > + > Create skill > Upload a skill**, choose `si-nmr-review.zip`, and make sure the skill is on.
4. In a new chat, upload the spectra (images, a ZIP of images, or an SI PDF; at most 20 files per chat) and write: *Use si-nmr-review to pre-screen these 1H spectra.* For the lenient rule set add: *use config/rubric.relaxed.json*.

To try it without your own data, upload [example-spectra.zip](https://github.com/1e32e3e/si-nmr-review/releases/latest/download/example-spectra.zip) (the 13 examples).

### 3. On your computer

Download the repository (GitHub's "Download ZIP" is fine here) and unzip it. Python 3.9+ with numpy, scipy and Pillow (`pip install -r requirements.txt`).

- **Demo**: double-click `run_demo.bat` (Windows) or run `sh run_demo.sh`. It grades the 13 examples with both rule sets and opens `demo_output/report.html`. The examples come with ready transcriptions, so no model is needed.
- **Your own spectra with Claude Code**: copy the `si-nmr-review` folder to `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`), start Claude Code in the folder with your spectra and ask *Use si-nmr-review to pre-screen these spectra.* Claude transcribes the printed labels and runs the scripts. The spectra and the scripts do not need to be in the same folder.
- **Your own spectra with Python only** (no AI at all):
  1. `python si-nmr-review/scripts/prepare_inputs.py <folder, ZIP or SI PDF> --out my/images` collects one image per spectrum.
  2. `python si-nmr-review/scripts/make_templates.py my/images my/labels` writes a blank label file per image.
  3. In each file fill at least `axis_labels` (e.g. `"11 to -1 step 0.5"`) and `integral_values` (the printed integrals, highest ppm first); the other fields (compound number, solvent, structure shown, labels such as EtOAc) refine the presentation checks.
  4. `python si-nmr-review/scripts/review_images.py my/images my/labels my/out` and `python si-nmr-review/scripts/report_html.py my/report.html "Rules=my/out"`.

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
| `scripts/report_html.py` | One HTML page with grades, reasons and overlays (several rule sets side by side) |
| `REVIEW_GUIDE.md`, `si-nmr-review-guide/` | The same rules written out for a model to follow without code (generated by `tools/build_guide.py`) |

## Results on the 13 examples

Against the group leader's own grades: the strict rubric is about 2.8 notches harsher on average (4 of 13 within one notch); the relaxed rubric matches 3 exactly and 5 within one notch. Both agree with him on the clearly failing spectra. The remaining differences come from context he applies (complex products, very small samples) and from what a screenshot cannot show (shimming, whether a mixture is reported in the text).

A second test (three blind runs per condition) compared Claude without code: given only the guidelines text, it was within one notch of the group leader on 10 of 13 (mean −0.3), but its results depend on the prompt and vary between runs (4-7 of 13 identical between pairs of runs). Given `REVIEW_GUIDE.md` as well, it reproduced the scripts' strict grades on 8-9 of 13 and agreed between runs on 10 of 13. It was also about 2.8 notches harsher than the group leader, like the strict rubric. The gap comes from the rules, not from how spectra are measured; recalibrating the rubric and regenerating the guide is the next step.

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
