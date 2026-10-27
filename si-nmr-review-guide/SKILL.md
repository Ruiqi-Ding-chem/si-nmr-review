---
name: si-nmr-review-guide
description: Review the 1H NMR spectra of an organic-chemistry Supporting Information file against the Wang group spectral guidelines by looking at the spectra, without running code, and suggest an E/V/S/N grade with reasons for each. Use when someone uploads SI spectrum images or an SI PDF and asks to check or grade the spectra and code execution is not available.
---

# Reviewing SI NMR spectra without code

This guide turns the Wang group spectral guidelines (2026-10-25) into a fixed procedure that you can follow by looking at the spectra. It is the same rule set the si-nmr-review scripts apply, written for a reader instead of a program. Give suggested grades with reasons for a human reviewer, never final grades.

## Procedure for each spectrum

1. **Read the page.** Note the ppm axis range, the printed integral values in order, the structure, the compound number, the frequency and the solvent if printed, labels such as “EtOAc” or “S.M”, and any insets. Zoom in on small text before trusting it.
2. **Find the solvent.** Use the printed solvent; otherwise the residual peak and the water peak tell you (table below). Check the residual peak sits at its literature shift; if not, note the offset.
3. **List every signal outside the author’s integrals** and classify it: residual solvent, water, grease (broad, near 1.26 and 0.86 in CDCl3), silicone grease (sharp, near 0.07), a common solvent (only if its pattern fits, e.g. EtOAc 2.05 s with 4.12 q), a 13C satellite (a small pair placed symmetrically about a large line, each about 0.55% of it, 0.1–0.35 ppm away), starting material (if the author labels it), or unknown. A product multiplet the author did not integrate is product, not an impurity.
4. **Measure, do not eyeball.** Compare each impurity signal with a product signal of known proton count (from the printed integrals) to get H-equivalents. Estimate purity as a range: low bound with each unknown signal as a separate 1H species, high bound as 3H; common solvents from their diagnostic line. Estimate the tallest peak as a fraction of the plot height, and the residual solvent and water peaks against the tallest product peak.
5. **Apply the rules below in order.** Base grade from purity, then deductions (within each group no more than the group limit), then caps, then context modifiers only for facts the author gave.
6. **Report** the grade, the purity range, each rule that fired with the value that triggered it, and the items a person must check. If a purity range straddles a grade boundary, give both grades and send it to a person.

Grades from low to high: N, S−, S, S+, V−, V, V+, E−, E. One step is one notch.

## Quantities used by the rules

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

## Base grade from purity

Purity used: the **mid** of the range (midpoint of low and high bound).
If purity cannot be estimated, start from **E** (the rules below then cap it).

| Purity at least (mol%) | Base grade |
|---|---|
| 99 | E |
| 98 | E- |
| 97 | V+ |
| 96 | V |
| 95 | V- |
| 92.5 | S+ |
| 90 | S |
| 85 | S- |
| 0 | N |

## Rules

Deductions in the same group add up to at most the group limit: impurity_unknown 2, starting_material 1, grease 2, c13_interference 1, isomer 2, dilution 2, display_height 1, data_display 2, integration 2, window 2, presentation 3, c13_snr 1.

| Rule | When | Effect | Group | Person checks | Why (the guidelines) |
|---|---|---|---|---|---|
| **1H purity cannot be estimated from the page** (1H) | NOT `purity_estimable` is yes | at most S | purity | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **Purity range straddles the 95% aim** (1H) | (`purity_mol_pct_low` < 95 AND `purity_mol_pct_high` ≥ 95) | flag | purity | yes | “the aim for all spectra published by the group is 95% or better purity of your claimed compound, by 1H NMR.” |
| **Purity range straddles the 90% floor** (1H) | (`purity_mol_pct_low` < 90 AND `purity_mol_pct_high` ≥ 90) | flag | purity | yes | “If there is a compound that is important for a project but cannot be purified to 90% purity (due to instability, volatility, acid-sensitivity, etc.), we should discuss whether to report it.” |
| **Purity certainly in the 90-95% tolerable band** (1H) | (`purity_mol_pct_low` ≥ 90 AND `purity_mol_pct_high` < 95) | flag | purity | yes | “If, after at least two additional attempts to repurify a sample, the purity is only between 90% and 95%, such spectra are tolerable.” |
| **Purity certainly below 90%** (1H) | `purity_mol_pct_high` < 90 | at most S- | purity | yes | “If there is a compound that is important for a project but cannot be purified to 90% purity (due to instability, volatility, acid-sensitivity, etc.), we should discuss whether to report it.” |
| **Below 95% only because of residual common solvent** (1H) | (`purity_mol_pct_low` < 95 AND `purity_excl_solvents_mol_pct_low` ≥ 95) | flag | purity | yes | “To minimize solvent peaks, you can repeatedly evaporate your sample from CDCl3 (or any other NMR solvent), sometimes directly in your NMR tube.” |
| **Unidentified impurity signals present** (1H) | `unknown_h_equiv` ≥ 0.05 | −1 | impurity_unknown |  | “In terms of undesirability, unidentified impurities are the worst” |
| **Prominent single unidentified signal** (1H) | `unknown_max_single_h_equiv` ≥ 0.2 | −1 | impurity_unknown | yes | “you should always work as hard as possible, including via multiple rounds of chromatography, crystallization, or distillation, to remove them.” |
| **Starting material present** (1H) | `sm_h_equiv` ≥ 0.05 | −1 | starting_material |  | “Any impurities, including starting material, solvents, or grease, must be minimized.” |
| **Residual common solvent large enough to check the yield** (1H) | `common_solvent_max_equiv` ≥ 0.1 | flag | solvent | yes | “there should not be so much that the yield calculation is no longer accurate, or interfere with assigning peaks in your 13C NMR.” |
| **An impurity is the tallest 1H peak** (1H) | `tallest_peak_class` is one of unknown, starting_material, common_solvent | flag | impurity_identity | yes | “Any impurities, including starting material, solvents, or grease, must be minimized.” |
| **Impurities labelled on the page** | (`impurity_labels_on_page` is known AND `impurity_labels_on_page` ≠ ) | flag | impurity_identity |  | “Any impurities, including starting material, solvents, or grease, must be minimized.” |
| **Grease visible (small amount)** (1H) | (`grease_h_equiv` ≥ 0.2 AND `grease_h_equiv` < 1) | flag | grease |  | “Solvent and grease are probably the most forgivable” |
| **Grease enough to affect yield accuracy** (1H) | (`grease_h_equiv` ≥ 1 OR (`grease_h_equiv` is unknown AND `grease_ratio` ≥ 0.5)) | −1 | grease |  | “there should not be so much that the yield calculation is no longer accurate, or interfere with assigning peaks in your 13C NMR.” |
| **Heavy grease or grease taller than the product** (1H) | (`grease_h_equiv` ≥ 3 OR `grease_ratio` ≥ 1 OR `tallest_peak_class` is one of grease, silicone_grease) | −1 | grease |  | “there should not be so much that the yield calculation is no longer accurate, or interfere with assigning peaks in your 13C NMR.” |
| **Non-product peak dominates the 13C spectrum** (13C) | (`tallest_peak_class` is one of grease, silicone_grease, common_solvent, unknown, starting_material OR `grease_ratio` ≥ 1) | −1 | c13_interference | yes | “there should not be so much that the yield calculation is no longer accurate, or interfere with assigning peaks in your 13C NMR.” |
| **Minor isomer integrated but not reported** (1H) | (`possible_minor_isomer` is yes AND `ctx_isomers_reported` is no) | −2 | isomer | yes | “If there are isomers that are inseparable, they must be noted in the main text and in the characterization section.” |
| **Possible minor isomer, reporting unknown** (1H) | (`possible_minor_isomer` is yes AND `ctx_isomers_reported` is unknown) | flag | isomer | yes | “If there are isomers that are inseparable, they must be noted in the main text and in the characterization section.” |
| **Residual solvent or water is the highest peak (dilute sample)** (1H) | (`tallest_peak_class` is one of residual_solvent, water OR `residual_solvent_ratio` > 1 OR `water_ratio` > 1) | −1 | dilution |  | “The sample should not be excessively dilute, meaning that residual proton of your NMR solvent and water should not be your highest peaks in the 1H NMR.” |
| **Residual solvent or water at least 3x the product** (1H) | (`residual_solvent_ratio` ≥ 3 OR `water_ratio` ≥ 3) | −1 | dilution |  | “The sample should not be excessively dilute, meaning that residual proton of your NMR solvent and water should not be your highest peaks in the 1H NMR.” |
| **1H baseline somewhat noisy** (1H) | (`baseline_noise_fraction` > 0.01 AND `baseline_noise_fraction` ≤ 0.02) | flag | dilution | yes | “The sample should not be excessively dilute, meaning that residual proton of your NMR solvent and water should not be your highest peaks in the 1H NMR.” |
| **1H noise high enough to hide impurities** (1H) | `baseline_noise_fraction` > 0.02 | −1 | dilution | yes | “The sample should not be excessively dilute, meaning that residual proton of your NMR solvent and water should not be your highest peaks in the 1H NMR.” |
| **Tallest peak well below 3/4 of display height** (1H) | `tallest_peak_fraction` < 0.6 | −1 | display_height |  | “Also, the tallest peak in your 1H NMR spectrum should rise to about ¾ up the total display height.” |
| **Tallest product peak clipped** (1H) | (`tallest_peak_clipped` is yes AND `tallest_peak_class` = product) | −1 | display_height |  | “Also, the tallest peak in your 1H NMR spectrum should rise to about ¾ up the total display height.” |
| **Tallest peak above about 3/4 (not a clipped product peak)** (1H) | (`tallest_peak_fraction` > 0.9 AND NOT (`tallest_peak_clipped` is yes AND `tallest_peak_class` = product)) | flag | display_height |  | “Also, the tallest peak in your 1H NMR spectrum should rise to about ¾ up the total display height.” |
| **Product signals displayed small** (1H) | (`tallest_product_peak_fraction` ≥ 0.2 AND `tallest_product_peak_fraction` < 0.4) | flag | hiding | yes | “In particular, it is not acceptable to use a low signal height to hide impurities in your spectrum.” |
| **Product signal height low enough to hide impurities** (1H) | `tallest_product_peak_fraction` < 0.2 | at most S | hiding | yes | “In particular, it is not acceptable to use a low signal height to hide impurities in your spectrum.” |
| **13C spectrum plotted with low signal height** (13C) | `tallest_peak_fraction` < 0.375 | flag | hiding | yes | “In particular, it is not acceptable to use a low signal height to hide impurities in your spectrum.” |
| **1H integrals not displayed** (1H) | `integrals_shown` is no | −2 | data_display |  | “Integration for 1H NMR and peak picking for 13C NMR should be displayed.” |
| **13C peak picking not displayed** (13C) | `peak_labels_shown` is no | −1 | data_display |  | “Integration for 1H NMR and peak picking for 13C NMR should be displayed.” |
| **Integral region includes residual solvent or water** (1H) | `integral_includes_solvent_or_water` is yes | −1 | integration | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **Several integrals far from whole numbers** (1H) | `integral_nonint_count` ≥ 2 | −1 | integration | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **Many integrals far from whole numbers** (1H) | `integral_nonint_count` ≥ 4 | −1 | integration | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **One integral far from a whole number** (1H) | `integral_nonint_count` = 1 | flag | integration |  | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **1H window cuts off part of the recommended range** (1H) | (`window_left_ppm` < 9.5 OR `window_right_ppm` > 0) | −1 | window | yes | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **1H window hides a large region** (1H) | (`window_left_ppm` < 8 OR `window_right_ppm` > 0.7) | −1 | window | yes | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **1H window much wider than recommended** (1H) | (`window_deviation_ppm` > 1 AND `window_left_ppm` ≥ 9.5 AND `window_right_ppm` ≤ 0) | −1 | window | yes | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **1H window slightly off the recommended range** (1H) | (`window_deviation_ppm` > 0.25 AND `window_deviation_ppm` ≤ 1) | flag | window |  | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **13C window cuts off part of the recommended range** (13C) | (`window_left_ppm` < 200 OR `window_right_ppm` > 0) | −1 | window | yes | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **13C window much wider than recommended** (13C) | (`window_deviation_ppm` > 10 AND `window_left_ppm` ≥ 200 AND `window_right_ppm` ≤ 0) | −1 | window | yes | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **13C window slightly off the recommended range** (13C) | (`window_deviation_ppm` > 5 AND `window_deviation_ppm` ≤ 10) | flag | window |  | “In general, I recommend a window of 10.5 ppm to –0.5 ppm for 1H NMR spectra and 210 ppm to –10 ppm for 13C NMR spectra.” |
| **Structure not shown** | `structure_shown` is no | −1 | presentation |  | “In general, the structure and the number of the compound should be displayed clearly.” |
| **Compound number not shown** | `compound_number_shown` is no | −1 | presentation |  | “In general, the structure and the number of the compound should be displayed clearly.” |
| **Instrument frequency missing where the journal requires it** | (`frequency_shown` is no AND (`ctx_journal_requires_freq_solvent` is yes OR `ctx_journal` is one of Org. Lett., Org. Lett, Org Lett, Organic Letters, OL)) | −1 | presentation |  | “Some journals, including Org. Lett., also require the indication of instrument frequency and NMR solvent on the displayed page.” |
| **NMR solvent missing where the journal requires it** | (`solvent_shown` is no AND (`ctx_journal_requires_freq_solvent` is yes OR `ctx_journal` is one of Org. Lett., Org. Lett, Org Lett, Organic Letters, OL)) | −1 | presentation |  | “Some journals, including Org. Lett., also require the indication of instrument frequency and NMR solvent on the displayed page.” |
| **Frequency or solvent missing, journal requirement unknown** | ((`frequency_shown` is no OR `solvent_shown` is no) AND `ctx_journal_requires_freq_solvent` is unknown AND NOT `ctx_journal` is one of Org. Lett., Org. Lett, Org Lett, Organic Letters, OL) | flag | presentation | yes | “Before you start putting together the SI, check the journal’s standards!” |
| **Complex compound shown without insets** (1H) | (`ctx_high_complexity` is yes AND `insets_present` is no) | −1 | presentation |  | “in order to clearly exhibit the couplings in complex compounds (especially diagnostic one that allow you to assign the structure or stereochemistry), you should use insets with relevant parts zoomed in.” |
| **No insets (complexity not stated)** (1H) | (`ctx_high_complexity` is unknown AND `insets_present` is no) | flag | presentation |  | “you should use insets with relevant parts zoomed in.” |
| **Page only fairly legible** | `legibility` = fair | −1 | presentation |  | “In general, the structure and the number of the compound should be displayed clearly.” |
| **Page illegible** | `legibility` = poor | at most S | legibility | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **Weakest 13C peak below S/N 1.5 (raw data)** (13C) | `c13_weakest_snr` < 1.5 | at most S | c13_snr | yes | “13C NMR spectra need to be collected with enough scans that the weakest peak has a signal to noise ratio of at least 1.5.” |
| **Very noisy 13C trace (image)** (13C) | (`c13_weakest_snr` is unknown AND `baseline_noise_fraction` > 0.05) | −1 | c13_snr | yes | “13C NMR spectra need to be collected with enough scans that the weakest peak has a signal to noise ratio of at least 1.5.” |
| **13C noise worth checking (image)** (13C) | (`c13_weakest_snr` is unknown AND `baseline_noise_fraction` > 0.02 AND `baseline_noise_fraction` ≤ 0.05) | flag | c13_snr | yes | “13C NMR spectra need to be collected with enough scans that the weakest peak has a signal to noise ratio of at least 1.5.” |
| **1H referencing offset** (1H) | (`calibration_offset_ppm` > 0.03 OR `calibration_offset_ppm` < -0.03) | flag | data_quality | yes | “NMR data should be presented in a way that conforms to journal standards.” |
| **13C referencing offset** (13C) | (`calibration_offset_ppm` > 0.3 OR `calibration_offset_ppm` < -0.3) | flag | data_quality | yes | “NMR data should be presented in a way that conforms to journal standards.” |
| **Baseline drift** | `baseline_drift_fraction` > 0.05 | flag | data_quality | yes | “The spectra you present in your Supporting Information file should provide evidence for identity and purity of the compounds you claim in your manuscript.” |
| **Broad lines (raw data)** (1H) | `linewidth_hz` > 1.5 | flag | data_quality |  | “in order to clearly exhibit the couplings in complex compounds” |
| **Short relaxation delay (raw data)** (1H) | `relaxation_delay_s` < 1 | flag | data_quality |  | “the aim for all spectra published by the group is 95% or better purity of your claimed compound, by 1H NMR.” |

## Context modifiers (only for facts the author supplied)

They give back notches; they never lift a grade above its purity band or past a cap from a blocker rule.

| Modifier | When | Effect | Note |
|---|---|---|---|
| CM-REASON-BELOW-90 | (`nucleus` = 1H AND `ctx_low_purity_reason_stated` is yes AND `purity_mol_pct_high` < 90) | +1 | Text-backed: a compound that cannot reach 90% may be reported with the reason stated and a purity-corrected or NMR yield. Adds one notch (N to S-). The PUR-BELOW-90 blocker cap keeps it at S- or lower, below the 90-95% band. Fires only when the whole purity range is below 90%; straddling cases go to human review. |
| CM-UNSTABLE | (`nucleus` = 1H AND `ctx_unstable` is yes AND `purity_mol_pct_low` < 95) | flag | Instability may explain purity below 95% and may make the two extra repurification attempts impractical. No automatic notch: the text ties relief for instability to the below-90 exception with a stated reason. The spectrum still counts toward the 2-3 per 40 SI limit; the reviewer weighs it. |
| CM-UNSTABLE-NO-REASON | (`ctx_unstable` is yes AND NOT `ctx_low_purity_reason_stated` is yes AND `purity_mol_pct_high` < 90) | flag | Unstable compound below 90%, but the SI does not state why it could not be purified. The standard requires that reason, so no notch is restored. |
| CM-SMALL-SAMPLE-DILUTION | (`nucleus` = 1H AND `ctx_small_sample` is yes AND (`tallest_peak_class` is one of residual_solvent, water OR `residual_solvent_ratio` > 1 OR `water_ratio` > 1 OR `baseline_noise_fraction` > 0.02)) | +1 | Inferred relaxation: a very small sample cannot always be concentrated enough to outgrow the residual solvent and water peaks or to give a quiet baseline. Gives back one dilution/noise notch. It does not touch the display-height rules or the HIDE-CAP blocker (vertical scaling is a plotting choice), grease (the text gives small-scale remedies) or 13C S/N (the remedy is more scans). |
| CM-SMALL-SAMPLE-GREASE | (`ctx_small_sample` is yes AND (`grease_h_equiv` ≥ 1 OR `grease_ratio` ≥ 0.5)) | flag | Small scale explains but does not excuse grease: the standard names small scale (<20 mg) and gives the remedies (n-pentane or n-hexane instead of hexanes, glass fiber or a frit instead of cotton, pipette column, prep TLC). The reviewer checks whether they were tried. |
| CM-COMPLEX | (`nucleus` = 1H AND `ctx_high_complexity` is yes AND (`integral_nonint_count` ≥ 2 OR (`unknown_h_equiv` ≥ 0.05 AND `unknown_max_single_h_equiv` < 0.2 AND NOT `possible_minor_isomer` is yes))) | +1 | Inferred relaxation (weak textual basis: the text links complexity to insets, not leniency). In highly complex products, overlapping multiplets, rotamers and diastereotopic signals make integrals non-integer or get read as small unknowns. Gives back one notch in total, never when a single unknown signal is 0.2 H-equiv or larger, and not for unknowns when a minor isomer is suspected (CM-ISOMERS-REPORTED handles that). |
| CM-ISOMERS-REPORTED | (`ctx_isomers_reported` is yes AND `possible_minor_isomer` is yes AND `unknown_h_equiv` ≥ 0.05) | +1 | The author reports an inseparable isomer mixture, as the standard requires. The minor-isomer signals were probably counted as unidentified impurity, so the UNK-PRESENT notch is given back. The reviewer recomputes purity with the declared mixture as the claimed compound and checks the ratio matches the main text and characterization entry. |
| CM-JOURNAL-NOT-REQUIRED | (`ctx_journal_requires_freq_solvent` is no AND (`frequency_shown` is no OR `solvent_shown` is no)) | flag | The author states the target journal does not require frequency or solvent on the page, so their absence is not deducted. |

## Things only a person can judge

- **Identity: the spectrum matches the claimed structure (shifts, multiplicities, proton counts, number of carbons)**: Assign the 1H signals (shift, multiplicity, integral) and count the 13C peaks against the unique carbons. Check that the drawn structure and compound number match the main text and the characterization entry.
- **Insets show the diagnostic couplings (not just any zoom), and whether insets are needed at all**: Find the couplings that prove structure or stereochemistry (vicinal J for cis/trans, olefin J for E/Z) and confirm an inset resolves them well enough to read J. Supply ctx_high_complexity so PRES-INSETS-COMPLEX can apply.
- **Inseparable isomers are noted in the main text and in the characterization section**: Search the substrate table or scheme and the characterization entry for the isomer ratio (dr, E/Z, rr). It must appear in both and match the minor-isomer integrals. Supply ctx_isomers_reported.
- **At least two additional repurification attempts for 90-95% samples**: For every spectrum flagged PUR-TOLERABLE-BAND or PUR-STRADDLE-95, ask the author or check the notebook for the extra chromatography, crystallization, distillation, pipette-column or prep-TLC rounds. Without them the spectrum is not yet 'tolerable' and should be redone.
- **Below-90% compounds: PI discussion, stated reason, purity-corrected or NMR yield**: Confirm the PI agreed to report the compound, that the characterization entry states the reason (instability, volatility, acid sensitivity) and that the yield is purity-corrected or an NMR yield against a named internal standard.
- **Yield accuracy given the residual solvent and grease content**: Convert to wt% with molecular weights: solvent wt% = equiv x MW(solvent) / MW(product); hydrocarbon grease about H-equiv x 7 g/mol and silicone about H-equiv x 12.3 g/mol, each divided by MW(product). Above about 2 wt%, check the reported yield was corrected.
- **Solvent or grease peaks interfering with 13C peak assignment**: Overlay known impurity shifts (CDCl3: grease about 29.7 ppm, silicone about 1.0 ppm, EtOAc 171.1/60.5/21.0/14.2 ppm) on the 13C peak list and check none coincides with or is mistaken for a product carbon.
- **13C S/N of at least 1.5 when grading from images**: Count the visible carbon peaks against the expected unique carbons and zoom on the weakest expected ones (quaternary, carbonyl, C-F doublets). A missing or noise-level carbon fails; request the FID when borderline.
- **Whether a low display height actually hides impurities**: Re-plot the raw data with the tallest product peak at about 3/4 of the display height (and then expanded 4-10x) and look for signals invisible on the submitted page. If hidden impurities appear, re-grade from the re-plotted spectrum.
- **Whether impurities are classified correctly (unknown vs common solvent vs starting material vs isomer)**: Check each impurity label and each unknown signal against residual-solvent shift tables and the starting-material spectrum. Reclassifying an 'unknown' as solvent changes the grade a lot; re-run the grading after reclassifying.
- **Conformity to the target journal's SI standards beyond frequency and solvent**: Read the target journal's author guidelines for spectra (labels, layout, referencing, file format) and check a sample of pages against them.
- **Page layout (two spectra stacked per portrait page is allowed)**: No deduction for stacking two spectra. Confirm the target journal allows it and that stacked spectra stay legible.
- **Justified wider windows**: If WIN-1H-WIDE or WIN-13C-WIDE fired, check whether the compound has signals beyond the recommended range (CO2H, CHO, chelated OH, ketone C=O above 210 ppm); if so, lift the deduction.
- **Clarity of the structure drawing (stereochemistry shown, number matches the text)**: Check stereocenters, counter-ions and the compound number on the page against the main text and the characterization entry.
- **Whether the compound is a starting material or catalyst rather than a product (purity expectations differ)**: Identify substrate and catalyst spectra in the SI. No feature records the role, so any leniency for substrates is a human decision (open question).
- **Effect of impure starting material or catalyst on failed catalytic reactions**: Not an SI grading item. Where failed substrates or negative results are reported, check that substrate and catalyst purity were documented before concluding.
- **Purification practice used to reduce solvent and grease**: Advisory only, not graded. When solvent or grease rules fire, include the remedies in the feedback: co-evaporation from CDCl3, n-pentane or n-hexane instead of hexanes, glass fiber or a frit instead of cotton, pipette columns, prep TLC.

## Whole-SI checks

- No more than 2 or 3 of every 40 1H spectra may sit in the 90-95% purity band.
- Most spectra should be in the V or E range.
- No more than 15-20% of spectra graded S.
- No spectrum graded S- or N.
- Every compound below 90% purity needs a PI decision, a stated reason and a corrected or NMR yield.
- Every spectrum suggesting an inseparable isomer mixture has the isomers reported.
- If the journal requires frequency and solvent, every page shows them.
- Every 13C spectrum has its weakest peak at S/N 1.5 or better.
- At most two spectra stacked per portrait SI page.
- Every claimed compound has its evidence spectra.
- Human-review workload summary.

## Solvent reference (1H, ppm)

Values to be checked against Fulmer et al., Organometallics 2010, 29, 2176.

| NMR solvent | Residual | Water | Grease | Silicone | Common solvents (diagnostic line first) |
|---|---|---|---|---|---|
| CDCl3 | 7.26 | 1.5–1.72 | 0.86, 1.26 | 0.07 | EtOAc 2.05 s, 4.12 q, 1.26 t; acetone 2.17 s; CH2Cl2 5.3 s; Et2O 3.48 q, 1.21 t; THF 3.76 m, 1.85 m; MeOH 3.49 s; MeCN 2.1 s; toluene 2.36 s; DMF 8.02 s, 2.96 s, 2.88 s; DMSO 2.62 s; Et3N 2.53 q, 1.03 t; iPrOH 4.04 sept, 1.22 d; EtOH 3.72 q, 1.25 t; cyclohexane 1.43 s |
| CD2Cl2 | 5.32 | 1.45–1.6 | 0.86, 1.27 | 0.09 | EtOAc 2 s, 4.05 q, 1.23 t; acetone 2.12 s; CHCl3 7.32 s; Et2O 3.43 q, 1.15 t; THF 3.69 m, 1.82 m; MeOH 3.42 s; MeCN 1.97 s; toluene 2.34 s; DMSO 2.52 s; cyclohexane 1.44 s |
| C6D6 | 7.16 | 0.35–0.5 | 0.92, 1.36 | 0.29 | EtOAc 1.65 s, 3.89 q, 0.92 t; acetone 1.55 s; CH2Cl2 4.27 s; CHCl3 6.15 s; Et2O 3.26 q, 1.11 t; THF 3.57 m, 1.4 m; MeOH 3.07 s; toluene 2.11 s |
| DMSO-d6 | 2.5 | 3.28–3.4 | 0.85, 1.24 | -0.06 | EtOAc 1.99 s, 4.03 q, 1.17 t; acetone 2.09 s; CH2Cl2 5.76 s; CHCl3 8.32 s; Et2O 3.38 q, 1.09 t; THF 3.6 m, 1.76 m; MeOH 3.16 s; DMF 7.95 s, 2.89 s, 2.73 s; toluene 2.3 s |
| CD3OD | 3.31 | 4.8–4.92 | 0.88, 1.29 | 0.1 | EtOAc 2.01 s, 4.09 q, 1.24 t; acetone 2.15 s; CH2Cl2 5.49 s; CHCl3 7.9 s; Et2O 3.49 q, 1.18 t; THF 3.71 m, 1.87 m |
| acetone-d6 | 2.05 | 2.78–2.9 | 0.87, 1.29 | 0.13 | EtOAc 1.97 s, 4.05 q, 1.2 t; CH2Cl2 5.63 s; CHCl3 8.02 s; Et2O 3.41 q, 1.11 t; THF 3.63 m, 1.79 m; MeOH 3.31 s |
| CD3CN | 1.94 | 2.1–2.2 | 0.86, 1.27 | 0.08 | EtOAc 1.97 s, 4.06 q, 1.2 t; acetone 2.08 s; CH2Cl2 5.44 s; CHCl3 7.58 s; THF 3.64 m, 1.8 m |

## Report format

A table with one row per spectrum: grade, purity range, main reasons. Then, per spectrum, every rule that fired with its value, and the items for a person. End with the whole-SI distribution against the target (mostly V or E, at most 15–20% S, no S− or N) and the reminder that the grades are suggestions.
