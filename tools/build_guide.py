"""Render the rubric (si-nmr-review/config/rubric.json) and the solvent table into a no-code review
guide that a model can follow by looking at spectra, without running any script.

    python tools/build_guide.py

Writes si-nmr-review-guide/SKILL.md (a skill folder with no scripts) and REVIEW_GUIDE.md (the same
text, for a claude.ai Project's knowledge). Regenerate whenever the rubric changes.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUBRIC = os.path.join(ROOT, "si-nmr-review", "config", "rubric.json")
SHIFTS = os.path.join(ROOT, "si-nmr-review", "config", "solvent_shifts.json")

OPS = {"<": "<", "<=": "≤", ">": ">", ">=": "≥", "==": "=", "!=": "≠", "in": "is one of", "not_in": "is not one of"}

FEATURES = """
| Quantity | Meaning |
|---|---|
| `structure_shown`, `compound_number_shown`, `frequency_shown`, `solvent_shown` | printed on the spectrum page (yes/no) |
| `integrals_shown`, `peak_labels_shown`, `insets_present` | integrals, ppm labels above peaks, zoomed insets drawn (yes/no) |
| `legibility` | good, fair (readable with effort) or poor (labels unreadable) |
| `window_left_ppm`, `window_right_ppm` | displayed ppm range |
| `window_deviation_ppm` | largest distance of either end from 10.5 / −0.5 (1H) or 210 / −10 (13C) |
| `impurity_labels_on_page`, `sm_labeled` | labels such as “EtOAc” or “S.M” printed by the author |
| `tallest_peak_class` | what the tallest peak is: product, residual_solvent, water, grease, silicone_grease, common_solvent, starting_material or unknown |
| `tallest_peak_fraction` | height of the tallest peak ÷ height from baseline to the top of the plot (1 if it runs off the top) |
| `tallest_peak_clipped` | the tallest peak runs off the top of the plot |
| `tallest_product_peak_fraction` | the same for the tallest product peak |
| `residual_solvent_ratio`, `water_ratio`, `grease_ratio` | height of that peak ÷ height of the tallest product peak |
| `purity_estimable` | integrals and trace can be read well enough to estimate purity |
| `purity_mol_pct_low`, `purity_mol_pct_high` | mol% of the claimed compound among the organic species seen (unknowns, starting material, common solvents; not water, residual NMR solvent or grease). Low bound: count each unknown signal as a separate 1H species; high bound: as 3H |
| `purity_excl_solvents_mol_pct_low/high` | the same without common solvents |
| `unknown_h_equiv`, `unknown_max_single_h_equiv` | total and largest unidentified signal, in units of one product proton |
| `sm_h_equiv` | starting-material signals, same units |
| `common_solvent_max_equiv` | largest molar equivalent of a common solvent per mole of product |
| `grease_h_equiv` | grease and silicone grease, in units of one product proton |
| `integral_includes_solvent_or_water` | an author’s integral region contains the residual solvent or water peak |
| `integral_nonint_count` | printed integrals (≥ 0.5) more than 0.15 from a whole number |
| `possible_minor_isomer` | two or more printed integrals between 0.05 and 0.4 |
| `calibration_offset_ppm` | position of the residual solvent peak minus its literature shift |
| `baseline_noise_fraction`, `baseline_drift_fraction` | noise and slow baseline deviation ÷ plot height |
| `c13_weakest_snr`, `linewidth_hz`, `relaxation_delay_s` | only from raw data; treat as unknown from an image |
| `ctx_…` | facts the author supplies (high complexity, small sample, unstable, isomers reported, reason for low purity stated, journal). Unknown unless given |
"""


def cond(c):
    if "all" in c:
        return "(" + " AND ".join(cond(x) for x in c["all"]) + ")"
    if "any" in c:
        return "(" + " OR ".join(cond(x) for x in c["any"]) + ")"
    if "not" in c:
        return "NOT " + cond(c["not"])
    f, op, v = c.get("feature"), c.get("op"), c.get("value")
    if op == "is_true":
        return f"`{f}` is yes"
    if op == "is_false":
        return f"`{f}` is no"
    if op == "is_null":
        return f"`{f}` is unknown"
    if op == "not_null":
        return f"`{f}` is known"
    if isinstance(v, list):
        v = ", ".join(str(x) for x in v)
    return f"`{f}` {OPS.get(op, op)} {v}"


def effect(r):
    if r["effect"] == "deduct":
        return f"−{r['notches']:g}"
    if r["effect"] == "cap":
        return f"at most {r['cap_grade']}"
    return "flag"


def main():
    with open(RUBRIC, encoding="utf-8") as f:
        rub = json.load(f)
    with open(SHIFTS, encoding="utf-8") as f:
        sh = json.load(f)

    L = []
    L += ["# Reviewing SI NMR spectra without code",
          "",
          "This guide turns the Wang group spectral guidelines (2026-10-25) into a fixed procedure that you can follow by looking at the spectra. It is the same rule set the si-nmr-review scripts apply, written for a reader instead of a program. Give suggested grades with reasons for a human reviewer, never final grades.",
          "",
          "## Procedure for each spectrum",
          "",
          "1. **Read the page.** Note the ppm axis range, the printed integral values in order, the structure, the compound number, the frequency and the solvent if printed, labels such as “EtOAc” or “S.M”, and any insets. Zoom in on small text before trusting it.",
          "2. **Find the solvent.** Use the printed solvent; otherwise the residual peak and the water peak tell you (table below). Check the residual peak sits at its literature shift; if not, note the offset.",
          "3. **List every signal outside the author’s integrals** and classify it: residual solvent, water, grease (broad, near 1.26 and 0.86 in CDCl3), silicone grease (sharp, near 0.07), a common solvent (only if its pattern fits, e.g. EtOAc 2.05 s with 4.12 q), a 13C satellite (a small pair placed symmetrically about a large line, each about 0.55% of it, 0.1–0.35 ppm away), starting material (if the author labels it), or unknown. A product multiplet the author did not integrate is product, not an impurity.",
          "4. **Measure, do not eyeball.** Compare each impurity signal with a product signal of known proton count (from the printed integrals) to get H-equivalents. Estimate purity as a range: low bound with each unknown signal as a separate 1H species, high bound as 3H; common solvents from their diagnostic line. Estimate the tallest peak as a fraction of the plot height, and the residual solvent and water peaks against the tallest product peak.",
          "5. **Apply the rules below in order.** Base grade from purity, then deductions (within each group no more than the group limit), then caps, then context modifiers only for facts the author gave.",
          "6. **Report** the grade, the purity range, each rule that fired with the value that triggered it, and the items a person must check. If a purity range straddles a grade boundary, give both grades and send it to a person.",
          "",
          "Grades from low to high: N, S−, S, S+, V−, V, V+, E−, E. One step is one notch.",
          "",
          "## Quantities used by the rules", FEATURES,
          "## Base grade from purity", "",
          f"Purity used: the **{rub['purity_basis']}** of the range" + (" (midpoint of low and high bound)." if rub["purity_basis"] == "mid" else "."),
          f"If purity cannot be estimated, start from **{rub['default_base_grade_if_purity_unknown']}** (the rules below then cap it).", "",
          "| Purity at least (mol%) | Base grade |", "|---|---|"]
    for row in sorted(rub["base_grade_table"], key=lambda r: -r["min_purity_mol_pct"]):
        L.append(f"| {row['min_purity_mol_pct']:g} | {row['grade']} |")
    L += ["", "## Rules", "",
          "Deductions in the same group add up to at most the group limit: "
          + ", ".join(f"{g} {n:g}" for g, n in rub.get("group_max_deduction", {}).items()) + ".", "",
          "| Rule | When | Effect | Group | Person checks | Why (the guidelines) |", "|---|---|---|---|---|---|"]
    for r in rub["rules"]:
        nuc = "" if r["nucleus"] == "any" else f" ({r['nucleus']})"
        L.append(f"| **{r['title']}**{nuc} | {cond(r['condition'])} | {effect(r)} | {r['group']} | {'yes' if r['human_review'] else ''} | “{r['standard_quote']}” |")
    L += ["", "## Context modifiers (only for facts the author supplied)", "",
          "They give back notches; they never lift a grade above its purity band or past a cap from a blocker rule.", "",
          "| Modifier | When | Effect | Note |", "|---|---|---|---|"]
    for m in rub["context_modifiers"]:
        eff = f"+{m['notches']:g}" if m["effect"] == "add" else "flag"
        L.append(f"| {m['id']} | {cond(m['condition'])} | {eff} | {m['note']} |")
    L += ["", "## Things only a person can judge", ""]
    for it in rub["not_computable_items"]:
        L.append(f"- **{it['item']}**: {it['how_a_human_checks']}")
    L += ["", "## Whole-SI checks", ""]
    for it in rub["si_level_checks"]:
        L.append(f"- {it['description']}")
    L += ["", "## Solvent reference (1H, ppm)", "",
          "Values to be checked against Fulmer et al., Organometallics 2010, 29, 2176.", "",
          "| NMR solvent | Residual | Water | Grease | Silicone | Common solvents (diagnostic line first) |", "|---|---|---|---|---|---|"]
    for name, sv in sh.items():
        if name.startswith("_"):
            continue
        sol = "; ".join(f"{k} " + ", ".join(f"{p[0]:g} {p[2]}" for p in v) for k, v in sv["solvents"].items())
        L.append(f"| {name} | {sv['residual']:g} | {sv['water'][0]:g}–{sv['water'][1]:g} | {', '.join(f'{g:g}' for g in sv['grease'])} | {sv['silicone']:g} | {sol} |")
    L += ["", "## Report format", "",
          "A table with one row per spectrum: grade, purity range, main reasons. Then, per spectrum, every rule that fired with its value, and the items for a person. End with the whole-SI distribution against the target (mostly V or E, at most 15–20% S, no S− or N) and the reminder that the grades are suggestions."]
    body = "\n".join(L) + "\n"

    front = ("---\nname: si-nmr-review-guide\n"
             "description: Review the 1H NMR spectra of an organic-chemistry Supporting Information file against the Wang group spectral guidelines by looking at the spectra, without running code, and suggest an E/V/S/N grade with reasons for each. Use when someone uploads SI spectrum images or an SI PDF and asks to check or grade the spectra and code execution is not available.\n---\n\n")
    os.makedirs(os.path.join(ROOT, "si-nmr-review-guide"), exist_ok=True)
    with open(os.path.join(ROOT, "si-nmr-review-guide", "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(front + body)
    with open(os.path.join(ROOT, "REVIEW_GUIDE.md"), "w", encoding="utf-8") as f:
        f.write(body)
    print(f"{len(body)} characters, {len(rub['rules'])} rules")


if __name__ == "__main__":
    main()
