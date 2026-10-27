"""Compute the rubric's features for one 1H spectrum from its digitized trace and its transcription.

Inputs:
  dig   - output of nmrimage.digitize() (ppm axis, heights above baseline, integral regions)
  ext   - transcription JSON (axis labels, integral values, printed text; see schemas/)
  ctx   - optional author-supplied context (ctx_* keys), or None

Every number here comes from fixed rules. The rules, thresholds and their
limits are written next to the code that applies them.
"""
import json
import os
import re

import numpy as np
from scipy.signal import find_peaks

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "config", "solvent_shifts.json"), encoding="utf-8") as f:
    SHIFTS = json.load(f)

TOL = 0.04             # ppm: a signal matches a known shift if its apex is this close
GREASE_TOL = 0.06      # ppm: grease lines are broad and wander (about 1.25-1.30 and 0.84-0.90 in CDCl3)
SEG_MIN_PX = 1.5       # columns above this height (or 2x noise) belong to a signal segment
DETECT_PX = 3.0        # a segment counts as a signal if its apex is this tall (or 4x noise)
SECOND_LINE_PX = 12.0  # a multi-line solvent needs a second line only if its diagnostic line is this tall
J_CH = (115.0, 215.0)  # Hz: range of one-bond 13C-H couplings, for 13C satellites
RECOMMENDED_1H = (10.5, -0.5)

SOLVENT_ALIASES = {
    "cdcl3": "CDCl3", "chloroform-d": "CDCl3", "cd2cl2": "CD2Cl2", "dichloromethane-d2": "CD2Cl2",
    "c6d6": "C6D6", "benzene-d6": "C6D6", "dmso-d6": "DMSO-d6", "dmso": "DMSO-d6", "(cd3)2so": "DMSO-d6",
    "cd3od": "CD3OD", "methanol-d4": "CD3OD", "acetone-d6": "acetone-d6", "(cd3)2co": "acetone-d6",
    "cd3cn": "CD3CN", "acetonitrile-d3": "CD3CN",
}
SOLVENT_LABELS = {"etoac": "EtOAc", "ea": "EtOAc", "ethyl acetate": "EtOAc", "acetone": "acetone",
                  "dcm": "CH2Cl2", "ch2cl2": "CH2Cl2", "et2o": "Et2O", "ether": "Et2O", "thf": "THF",
                  "meoh": "MeOH", "mecn": "MeCN", "toluene": "toluene", "dmf": "DMF", "et3n": "Et3N"}
SM_WORDS = re.compile(r"^(s\.?\s?m\.?|starting material|sm)$", re.I)


SUBSCRIPTS = str.maketrans("\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089", "0123456789")


def normalize_solvent(text):
    t = (text or "").translate(SUBSCRIPTS).strip().lower().replace(" ", "")
    for k, v in SOLVENT_ALIASES.items():
        if k in t:
            return v
    return None


def field_mhz(ext):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(MHz|GHz)", ext.get("frequency_text") or "", re.I)
    if not m:
        return None
    v = float(m.group(1)) * (1000.0 if m.group(2).lower() == "ghz" else 1.0)
    return v if v > 0 else None


def segments(h, noise, cuts=()):
    """Signal clusters: runs of columns above the segment threshold.

    A run is split where the trace returns to the baseline between two lines and at
    the edges of integral brackets, so an impurity next to a product multiplet, or a
    water line at the edge of an integral, is not swallowed by it. Each piece records
    whether a side was cut at a bracket edge (rather than ending at the baseline).
    """
    thr = max(SEG_MIN_PX, 2.0 * noise)
    valley = max(2.0, 3.0 * noise)
    above = h > thr
    d = np.diff(np.concatenate([[0], above.astype(np.int8), [0]]))
    runs = list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))
    cuts = sorted(set(int(c) for c in cuts))
    out = []
    for s, e in runs:
        pieces, start = [], s
        for i in range(s + 1, e - 1):
            if h[i] <= valley and h[i] <= h[i - 1] and h[i] <= h[i + 1]:
                pieces.append((start, i))
                start = i + 1
        pieces.append((start, e))
        for a, b in pieces:
            inner = [c for c in cuts if a < c < b]
            left_cut = False
            for c in inner:
                out.append((a, c, left_cut, True))
                a, left_cut = c, True
            out.append((a, b, left_cut, False))
    keep = []
    for a, b, lc, rc in out:
        if b > a and h[a:b].max() >= max(DETECT_PX, 4.0 * noise):
            keep.append((int(a), int(b), lc, rc))
    return keep


def lines_in(h, s, e, noise, left_cut=False, right_cut=False):
    """Local maxima inside a segment. A side cut at a bracket edge is padded with the
    neighbouring trace value, not zero, so the cut column is not mistaken for a line."""
    left = h[s - 1] if (left_cut and s > 0) else 0.0
    right = h[e] if (right_cut and e < len(h)) else 0.0
    pk, _ = find_peaks(np.concatenate([[left], h[s:e], [right]]), prominence=max(DETECT_PX, 4.0 * noise) * 0.6)
    return [s + p - 1 for p in pk]


def dominant_line(h, li, half_px):
    """True if line li stands well above everything within half_px columns, except its own +-1 shoulders."""
    lo, hi = max(0, li - half_px), min(len(h), li + half_px + 1)
    nb = np.concatenate([h[lo:max(lo, li - 1)], h[min(hi, li + 2):hi]])
    return nb.size == 0 or h[li] >= 1.5 * nb.max()


def residual_candidate(h, ppm, li, in_region, edge_px, dppm, clipped=None):
    """A line counts as a residual-solvent line if it is outside the integrals (or within edge_px of a
    bracket edge), if its apex is clipped at the plot top, or, inside an integral, if it is the tallest
    line within 0.1 ppm and stands at least 30% of its height above the deeper of its two flanking
    minima (a solvent spike on top of a multiplet, not one line of an even multiplet)."""
    lo, hi = max(0, li - edge_px), min(len(h), li + edge_px + 1)
    if not in_region[lo:hi].all():
        return True
    if clipped is not None and clipped[li]:
        return True
    w = max(3, int(round(0.1 / dppm)))
    a, b = max(0, li - w), min(len(h), li + w + 1)
    seg = h[a:b].copy()
    seg[max(0, li - a - 1):li - a + 2] = 0
    if h[li] < 1.15 * seg.max():
        return False
    left, k = h[li], li
    while k > a and h[k - 1] <= h[k]:
        k -= 1
    left = h[k]
    right, k = h[li], li
    while k < b - 1 and h[k + 1] <= h[k]:
        k += 1
    right = h[k]
    return h[li] - max(left, right) >= 0.3 * h[li]


def infer_solvent(seg_info, ppm, h, in_region, dppm, clipped=None):
    """Pick the NMR solvent when the page does not print it.

    CDCl3 unless its residual line is absent and another solvent shows both a residual line
    outside the integrals and an isolated singlet in its water window.
    """
    def residual_lines(sv):
        return [li for sg in seg_info for li in sg["lines"]
                if abs(ppm[li] - sv["residual"]) <= TOL and residual_candidate(h, ppm, li, in_region, 1, dppm, clipped)]

    if residual_lines(SHIFTS["CDCl3"]):
        return "CDCl3", "inferred (CHCl3 line present)"
    best = None
    for name, sv in SHIFTS.items():
        if name.startswith("_") or name == "CDCl3":
            continue
        outside = [li for li in residual_lines(sv) if not in_region[li]]
        if not outside:
            continue
        water = any(sv["water"][0] <= ppm[li] <= sv["water"][1]
                    and not any(lj != li and abs(ppm[lj] - ppm[li]) <= 0.03 for lj in sg["lines"])
                    for sg in seg_info for li in sg["lines"])
        if water:
            hh = max(h[li] for li in outside)
            if best is None or hh > best[1]:
                best = (name, hh)
    if best:
        return best[0], "inferred (residual line outside the integrals and water line)"
    return "CDCl3", "assumed (default)"


def identify_solvents(cands, sv, at, labelled):
    """Assign common-solvent lines.

    A solvent counts only if its first (diagnostic) line is seen. A solvent whose
    diagnostic line is not a singlet, or that has several lines and a tall enough
    diagnostic line, also needs a second line of consistent size (lines that would sit
    under the grease do not count either way). A solvent named on the page needs only
    the diagnostic line. Pieces cut at a bracket edge with no line of their own are product flanks.
    Returns name -> list of matched segments.
    """
    found = {}
    for name, peaks in sv["solvents"].items():
        hits, used = [], set()
        for k, (sp, nh, mult) in enumerate(peaks):
            under_grease = any(abs(sp - g) <= GREASE_TOL for g in sv["grease"])
            best = None
            for sg in cands:
                if sg.get("cls") is not None or sg.get("solvent") or (sg["cut"] and not sg["lines"]) or id(sg) in used:
                    continue
                near = [li for li in sg["lines"] if abs(sg["ppm_of"](li) - at(sp)) <= TOL]
                if not near or (mult == "s" and len(sg["lines"]) > 2):
                    continue
                if best is None or abs(sg["ppm"] - at(sp)) < abs(best["ppm"] - at(sp)):
                    best = sg
            if best is not None:
                used.add(id(best))
            hits.append((k, best, nh, under_grease))
        diag = hits[0][1]
        if diag is None:
            continue
        per_h_diag = diag["area"] / hits[0][2]
        if per_h_diag <= 0:
            continue
        consistent = [x for x in hits[1:] if x[1] is not None and not x[3]
                      and 0.4 <= (x[1]["area"] / x[2]) / per_h_diag <= 2.5]
        visible_others = [x for x in hits[1:] if not x[3]]
        if name not in labelled:
            if peaks[0][2] != "s" and not consistent:
                continue          # a multiplet diagnostic line alone cannot identify the solvent
            if peaks[0][2] == "s" and visible_others and diag["h"] >= SECOND_LINE_PX and not consistent:
                continue          # its other lines should be visible but are not
        chosen = [hits[0]] + consistent
        for k, sg, nh, under_grease in chosen:
            sg["cls"], sg["solvent"], sg["solvent_peak"], sg["nH"] = "common_solvent", name, k, nh
            found.setdefault(name, []).append(sg)
    return found


def split_lobe(seg_info, sg, li, h, ppm):
    """Replace segment sg by the lobe of line li (walking downhill from it) plus the remaining pieces,
    which keep their own lines and are classified separately. Returns the lobe segment."""
    others = [lj for lj in sg["lines"] if lj != li]
    if not others:
        return sg
    a, b = li, li + 1
    while a > sg["s"] and h[a - 1] <= h[a]:
        a -= 1
    while b < sg["e"] and h[b] <= h[b - 1]:
        b += 1
    pieces = [(sg["s"], a), (a, b), (b, sg["e"])]
    new = []
    for s, e in pieces:
        if e - s < 1:
            continue
        lines = [lj for lj in sg["lines"] if s <= lj < e]
        if s != a and not lines:
            continue
        apex = li if s == a else max(lines, key=lambda j: h[j])
        lb = min(float(h[s]), float(h[e - 1]))
        new.append(dict(sg, s=s, e=e, apex=apex, ppm=float(ppm[apex]), h=float(h[apex] - lb), h_abs=float(h[apex]),
                        area=float(np.clip(h[s:e] - lb, 0, None).sum()), width_px=e - s, lines=lines, cut=sg["cut"]))
    idx = seg_info.index(sg)
    seg_info[idx:idx + 1] = new
    return next(x for x in new if x["s"] == a)


def compute(dig, ext, ctx=None):
    ppm, h = dig["ppm"], dig["h"]
    display = dig["display_px"]
    n = len(h)
    dppm = dig["ppm_per_px"]
    clipped_cols = dig["clipped"]

    # noise: spread of the trace in quiet columns (zero for a clean rendered baseline)
    quiet = h[h <= np.percentile(h, 70)]
    noise = float(1.4826 * np.median(np.abs(quiet - np.median(quiet)))) if quiet.size else 0.0

    # product regions = integral brackets on the page, matched to the transcribed values by order
    regions = []
    for (x0, x1), (p0, p1) in zip(dig["regions_px"], dig["regions_ppm"]):
        regions.append({"i0": int(x0 - dig["x_left"]), "i1": int(x1 - dig["x_left"]), "ppm": (p0, p1)})
    vals = list(ext.get("integral_values") or [])
    integrals_matched = len(vals) == len(regions) and len(vals) > 0
    if integrals_matched:
        for r, v in zip(regions, vals):
            r["value"] = float(v)
    in_region = np.zeros(n, bool)
    for r in regions:
        in_region[max(0, r["i0"]):min(n, r["i1"] + 1)] = True

    def region_of(i):
        return next((r for r in regions if r["i0"] <= i <= r["i1"]), None)

    cuts = [c for r in regions for c in (r["i0"], r["i1"] + 1)]
    pk, _ = find_peaks(np.concatenate([[0.0], h, [0.0]]), prominence=max(DETECT_PX, 4.0 * noise) * 0.6)
    all_lines = [int(p) - 1 for p in pk]
    seg_info = []
    for s, e, lc, rc in segments(h, noise, cuts):
        apex = s + int(np.argmax(h[s:e]))
        # area above a local baseline, so a small line on the foot of a big one is not credited with the foot
        lb = min(float(h[max(0, s - 3):s + 1].min()), float(h[max(s, e - 1):min(n, e + 3)].min()))
        seg_info.append({"s": s, "e": e, "cut": bool(lc or rc), "apex": apex, "ppm": float(ppm[apex]),
                         "h": float(h[apex] - lb), "h_abs": float(h[apex]),
                         "area": float(np.clip(h[s:e] - lb, 0, None).sum()), "width_px": e - s,
                         "in_region": bool(in_region[s:e].mean() > 0.5),
                         "lines": [li for li in all_lines if s <= li < e], "ppm_of": lambda i: float(ppm[i])})
        sg = seg_info[-1]
        if sg["cut"] and sg["lines"]:
            # a piece cut at a bracket edge that holds its own line: measure that line only, not the
            # product flank it shares the piece with
            li = max(sg["lines"], key=lambda j: h[j])
            a_, b_ = li, li + 1
            while a_ > s and h[a_ - 1] <= h[a_]:
                a_ -= 1
            while b_ < e and h[b_] <= h[b_ - 1]:
                b_ += 1
            valleys = ([float(h[a_])] if a_ < li else []) + ([float(h[b_ - 1])] if b_ - 1 > li else [])
            lb2 = max(valleys) if valleys else lb
            if np.clip(h[a_:b_] - lb2, 0, None).sum() <= 0 and valleys:
                lb2 = min(valleys)
            sg.update({"apex": li, "ppm": float(ppm[li]), "h": float(h[li] - lb2), "h_abs": float(h[li]),
                       "area": float(np.clip(h[a_:b_] - lb2, 0, None).sum())})

    # solvent: as printed, else inferred from residual and water lines
    solvent = normalize_solvent(ext.get("solvent_text"))
    solvent_source = "printed" if solvent else None
    if not solvent:
        solvent, solvent_source = infer_solvent(seg_info, ppm, h, in_region, dppm, clipped_cols)
    sv = SHIFTS[solvent]
    half = max(2, int(round(0.02 / dppm)))

    # residual NMR-solvent line: the tallest sharp line near its literature shift, inside or outside an
    # integral (inside, it must stand out from the product lines around it)
    res_line, res_seg, offset_note = None, None, ""
    for sg in seg_info:
        for li in sg["lines"]:
            if abs(ppm[li] - sv["residual"]) <= TOL and residual_candidate(h, ppm, li, in_region, 1, dppm, clipped_cols):
                if res_line is None or h[li] > h[res_line]:
                    res_line, res_seg = li, sg
    # miscalibration: only when nothing at all sits at the expected shift, take the tallest isolated
    # singlet outside the integrals within 0.3 ppm of it
    empty_there = not (np.abs(ppm - sv["residual"]) <= 0.05).any() or \
        h[np.abs(ppm - sv["residual"]) <= 0.05].max() < max(DETECT_PX, 4 * noise)
    if res_line is None and empty_there:
        near = [(sg, li) for sg in seg_info if not sg["in_region"] for li in sg["lines"]
                if abs(ppm[li] - sv["residual"]) <= 0.30 and len(sg["lines"]) == 1 and h[li] >= 0.01 * display]
        if near:
            near = [max(near, key=lambda t: h[t[1]])]
            res_seg, res_line = min(near, key=lambda t: abs(ppm[t[1]] - sv["residual"]))
            offset_note = "residual peak not at its literature shift; nearest isolated singlet used"
    if res_seg is not None and not res_seg["in_region"]:
        res_seg = split_lobe(seg_info, res_seg, res_line, h, ppm)
    offset = float(ppm[res_line] - sv["residual"]) if res_line is not None else 0.0
    calibration_offset = round(offset, 3) if res_line is not None else None
    if res_seg is not None and not res_seg["in_region"]:
        res_seg["cls"] = "residual_solvent"

    def at(x):
        return x + offset

    # water: the tallest isolated singlet line in the water window, inside or outside an integral
    water_line, water_seg = None, None
    w0, w1 = at(sv["water"][0]), at(sv["water"][1])
    for sg in seg_info:
        for li in sg["lines"]:
            if not (w0 <= ppm[li] <= w1):
                continue
            if any(lj != li and abs(ppm[lj] - ppm[li]) <= 0.03 and h[lj] > 0.3 * h[li] for lj in sg["lines"]):
                continue
            if in_region[li] and not dominant_line(h, li, max(half, int(round(0.06 / dppm)))):
                continue      # not a dominant spike: likely part of the product multiplet
            if water_line is None or h[li] > h[water_line]:
                water_line, water_seg = li, sg
    if water_seg is not None and not water_seg["in_region"]:
        water_seg = split_lobe(seg_info, water_seg, water_line, h, ppm)
        water_seg["cls"] = "water"

    # classify every unintegrated segment
    sm_marks = [a["approx_ppm"] for a in ext.get("annotations", []) if SM_WORDS.match(a["text"].strip())]
    labelled = {SOLVENT_LABELS[a["text"].strip().lower()] for a in ext.get("annotations", [])
                if a["text"].strip().lower() in SOLVENT_LABELS}
    grease_pos = [at(g) for g in sv["grease"]]
    free = [sg for sg in seg_info if not sg["in_region"] and "cls" not in sg]
    for sg in free:
        if any(abs(sg["ppm"] - a) <= 0.08 for a in sm_marks):
            sg["cls"] = "starting_material"
        elif abs(sg["ppm"] - at(sv["silicone"])) <= TOL:
            sg["cls"] = "silicone_grease"
    found_solvents = identify_solvents([sg for sg in free if "cls" not in sg], sv, at, labelled)
    for sg in free:
        if "cls" in sg:
            continue
        if any(abs(sg["ppm"] - g) <= GREASE_TOL for g in grease_pos):
            sg["cls"] = "grease"
        elif sg["cut"] and not sg["lines"]:
            sg["cls"] = "product"      # the author's bracket stops on the flank of this multiplet
        else:
            sg["cls"] = None

    # 13C satellites: small lines at +-J(CH)/2 from a big line, each about 0.55% of its area
    mhz = field_mhz(ext)
    f_lo, f_hi = (mhz, mhz) if mhz else (300.0, 600.0)
    d_lo, d_hi = J_CH[0] / 2 / f_hi - 0.01, J_CH[1] / 2 / f_lo + 0.01
    big = [sg for sg in seg_info if (sg["h_abs"] > 40 or clipped_cols[sg["apex"]])
           and sg.get("cls") not in ("water", "grease", "silicone_grease")]
    occupied = in_region | (h > 0)

    def mirror_ok(sg, b):
        m_ppm = 2 * b["ppm"] - sg["ppm"]
        j = int(np.argmin(np.abs(ppm - m_ppm)))
        if abs(ppm[j] - m_ppm) > 0.03:
            return True        # mirror position is off the displayed window
        lo, hi = max(0, j - 2), min(n, j + 3)
        if in_region[lo:hi].any():
            return True        # hidden under an integrated multiplet
        return h[lo:hi].max() >= 0.3 * sg["h"]

    for sg in seg_info:
        if sg.get("cls") is not None or sg["in_region"]:
            continue
        for b in big:
            d = abs(sg["ppm"] - b["ppm"])
            ratio = sg["area"] / b["area"] if b["area"] > 0 else 1.0
            ok_ratio = ratio >= 0.002 and (ratio <= 0.012 or (clipped_cols[b["apex"]] and sg["h"] <= 0.03 * display))
            if d_lo <= d <= d_hi and ok_ratio and mirror_ok(sg, b):
                sg["cls"] = "c13_satellite"
                sg["parent_ppm"] = b["ppm"]
                break
        if sg.get("cls") is None:
            sg["cls"] = "unknown"
    for sg in seg_info:
        if sg["in_region"] and "cls" not in sg:
            sg["cls"] = "product"

    # area of one product proton, from the integrals that do not contain the solvent or water line
    per_h, used = [], []
    for r in regions:
        v = r.get("value")
        if v is None or v < 0.5:
            continue
        if (res_line is not None and r["i0"] <= res_line <= r["i1"]) or \
           (water_line is not None and r["i0"] <= water_line <= r["i1"]):
            continue
        area = float(h[max(0, r["i0"]):min(n, r["i1"] + 1)].sum())
        if area > 0:
            per_h.append(area / v)
            used.append(round(v, 2))
    # robust: drop regions whose area per proton is far from the median (mis-matched or empty regions)
    if len(per_h) >= 3:
        med = float(np.median(per_h))
        kept = [x for x in per_h if 0.5 * med <= x <= 2.0 * med]
        a_h = float(np.median(kept)) if kept else med
    elif per_h:
        a_h = float(min(per_h)) if max(per_h) > 2 * min(per_h) else float(np.mean(per_h))
    else:
        a_h = None
    purity_estimable = bool(a_h and a_h > 0 and ext.get("legibility") != "poor")

    def heq(sg):
        return sg["area"] / a_h if a_h else None

    unknown = [sg for sg in seg_info if sg["cls"] == "unknown"]
    sm = [sg for sg in seg_info if sg["cls"] == "starting_material"]
    grease = [sg for sg in seg_info if sg["cls"] in ("grease", "silicone_grease")]

    # common solvents: moles from the diagnostic line
    solvent_equiv = {}
    for name, sgs in found_solvents.items():
        diag = sorted(sgs, key=lambda g: g["solvent_peak"])[0]
        if a_h:
            solvent_equiv[name] = diag["area"] / (diag["nH"] * a_h)
    # a solvent line hidden under the grease (EtOAc CH3 in CDCl3): its expected area is taken off the grease
    if a_h:
        for name, eq in solvent_equiv.items():
            for sp, nh, mult in sv["solvents"][name]:
                if not any(abs(sp - g) <= GREASE_TOL for g in sv["grease"]):
                    continue
                expect = nh * eq * a_h
                for sg in grease:
                    if sg["cls"] == "grease" and abs(sg["ppm"] - at(sp)) <= GREASE_TOL:
                        rest = max(0.0, sg.get("area_after_solvent", sg["area"]) - expect)
                        sg["area_after_solvent"] = rest
                        if rest < 0.3 * sg["area"]:
                            sg["cls"], sg["solvent"] = "common_solvent", name
    grease = [sg for sg in seg_info if sg["cls"] in ("grease", "silicone_grease")]

    if purity_estimable:
        u = [heq(sg) for sg in unknown]
        s_ = [heq(sg) for sg in sm]
        solv = sum(solvent_equiv.values())
        pur = lambda x: 100.0 / (1.0 + x)
        # signals marked as starting material belong to one species: its moles come from the mean signal
        sm_mol = float(np.mean(s_)) if s_ else 0.0
        p_low = pur(sum(u) + sm_mol + solv)
        p_high = pur(sum(u) / 3 + sm_mol / 3 + solv)
        px_low = pur(sum(u) + sm_mol)
        px_high = pur(sum(u) / 3 + sm_mol / 3)
        grease_heq = sum(sg.get("area_after_solvent", sg["area"]) for sg in grease) / a_h
    else:
        p_low = p_high = px_low = px_high = grease_heq = None

    # display: fractions of the display height
    res_pos = float(ppm[res_line]) if res_line is not None else at(sv["residual"])
    near_solvent = np.abs(ppm - res_pos) <= 0.025 if res_line is not None else np.zeros(n, bool)
    if water_line is not None:
        near_solvent |= np.abs(ppm - ppm[water_line]) <= 0.02
    prod_cols = in_region & ~near_solvent
    tallest_prod = float(h[prod_cols].max()) if prod_cols.any() else None
    imax = int(np.argmax(h))
    tied = np.where(h >= h[imax])[0]
    if clipped_cols[imax] and near_solvent[tied].any():
        imax = int(tied[near_solvent[tied]][0])
    if near_solvent[imax]:
        tallest_cls = "residual_solvent" if (res_line is not None and abs(ppm[imax] - res_pos) <= 0.025) else "water"
    elif prod_cols[imax]:
        tallest_cls = "product"
    else:
        owner = next((sg for sg in seg_info if sg["s"] <= imax < sg["e"]), None)
        tallest_cls = owner["cls"] if owner else "unknown"
        if tallest_cls == "c13_satellite":
            tallest_cls = "unknown"
    clipped = bool(clipped_cols.any())

    def ratio(x):
        return round(x / tallest_prod, 3) if (x is not None and tallest_prod) else None

    res_h = float(h[res_line]) if res_line is not None else None
    water_h = float(h[water_line]) if water_line is not None else None
    grease_h = max((sg["h_abs"] for sg in grease if sg["cls"] == "grease"), default=None)

    # integrals as printed
    int_nonint = sum(1 for v in vals if v >= 0.5 and abs(v - round(v)) > 0.15)
    minor = sum(1 for v in vals if 0.05 <= v <= 0.4) >= 2
    inc_solv = bool((res_line is not None and in_region[res_line]) or (water_line is not None and in_region[water_line]))

    # baseline shape: slow deviation of the baseline from a straight line
    base = dig["base"]
    quiet_cols = np.where(h <= max(SEG_MIN_PX, 2 * noise))[0]
    if quiet_cols.size > 10:
        bq = dig["base"][quiet_cols] + 0.0
        # the trace bottom in signal-free columns is the true baseline there
        bq = dig["bottom"][quiet_cols] if "bottom" in dig else bq
        lin = np.polyval(np.polyfit(quiet_cols, bq, 1), quiet_cols)
        drift = float(np.max(np.abs(bq - lin)) / display)
    else:
        drift = 0.0

    win = dig["window_ppm"]
    labels = [a["text"].strip() for a in ext.get("annotations", [])]
    feats = {
        "nucleus": "1H",
        "structure_shown": bool(ext.get("structure_drawn")),
        "compound_number_shown": bool((ext.get("compound_number") or "").strip()),
        "frequency_shown": bool((ext.get("frequency_text") or "").strip()),
        "solvent_shown": bool((ext.get("solvent_text") or "").strip()),
        "integrals_shown": bool(vals) or bool(regions),
        "peak_labels_shown": bool(ext.get("peak_labels_printed")),
        "insets_present": bool(ext.get("insets")),
        "legibility": ext.get("legibility", "good"),
        "window_left_ppm": round(win[0], 2), "window_right_ppm": round(win[1], 2),
        "window_deviation_ppm": round(max(abs(win[0] - RECOMMENDED_1H[0]), abs(win[1] - RECOMMENDED_1H[1])), 2),
        "impurity_labels_on_page": labels,
        "sm_labeled": bool(sm_marks),
        "tallest_peak_class": tallest_cls,
        "tallest_peak_fraction": round(min(1.0, float(h.max()) / display), 3),
        "tallest_peak_clipped": clipped,
        "tallest_product_peak_fraction": round(tallest_prod / display, 3) if tallest_prod else None,
        "residual_solvent_ratio": ratio(res_h),
        "water_ratio": ratio(water_h),
        "grease_ratio": ratio(grease_h),
        "purity_estimable": purity_estimable,
        "purity_mol_pct_low": r1(p_low), "purity_mol_pct_high": r1(p_high),
        "purity_excl_solvents_mol_pct_low": r1(px_low), "purity_excl_solvents_mol_pct_high": r1(px_high),
        "unknown_h_equiv": r3(sum(heq(sg) for sg in unknown)) if a_h else None,
        "unknown_max_single_h_equiv": r3(max((heq(sg) for sg in unknown), default=0.0)) if a_h else None,
        "sm_h_equiv": r3(sum(heq(sg) for sg in sm)) if a_h else None,
        "common_solvent_max_equiv": r3(max(solvent_equiv.values(), default=0.0)) if a_h else None,
        "grease_h_equiv": r3(grease_heq),
        "integral_includes_solvent_or_water": inc_solv,
        "integral_nonint_count": int(int_nonint),
        "possible_minor_isomer": bool(minor),
        "calibration_offset_ppm": calibration_offset,
        "baseline_noise_fraction": round(noise / display, 4),
        "baseline_drift_fraction": round(drift, 4),
        "linewidth_hz": None, "c13_weakest_snr": None, "relaxation_delay_s": None,
    }
    for k in ("ctx_high_complexity", "ctx_small_sample", "ctx_unstable", "ctx_isomers_reported",
              "ctx_low_purity_reason_stated", "ctx_journal", "ctx_journal_requires_freq_solvent"):
        feats[k] = (ctx or {}).get(k)

    evidence = {
        "solvent": solvent, "solvent_source": solvent_source, "calibration_note": offset_note,
        "residual_ppm": round(float(ppm[res_line]), 3) if res_line is not None else None,
        "noise_px": round(noise, 2), "display_px": display, "plot_top_px": dig.get("plot_top"),
        "ppm_per_px": round(dppm, 4),
        "detection_limit_h_equiv": r3(max(DETECT_PX, 4 * noise) * 2 / a_h) if a_h else None,
        "integrals_matched_to_brackets": integrals_matched, "region_source": dig.get("region_source"),
        "n_brackets": len(regions), "n_integral_values": len(vals),
        "per_h_area_from_integrals": used,
        "solvent_equiv": {k: r3(v) for k, v in solvent_equiv.items()},
        "water_ppm": round(float(ppm[water_line]), 2) if water_line is not None else None,
        "signals": [
            {"ppm": round(sg["ppm"], 2), "class": sg["cls"], "height_frac": round(sg["h"] / display, 4),
             "h_equiv": r3(heq(sg)) if a_h else None, "solvent": sg.get("solvent"),
             "lines": len(sg["lines"])}
            for sg in sorted(seg_info, key=lambda g: -g["ppm"]) if sg["cls"] != "product"
        ],
        "axis_fit": dig["axis_fit"],
    }
    for sg in seg_info:
        sg.pop("ppm_of", None)
    return feats, evidence, seg_info


def presentation_only(ext, ctx, reason):
    """Features when the trace cannot be digitized: page facts from the transcription, the rest unknown."""
    labels = ext.get("axis_labels") or []
    left, right = (max(labels), min(labels)) if labels else (None, None)
    feats = {
        "nucleus": "1H",
        "structure_shown": bool(ext.get("structure_drawn")),
        "compound_number_shown": bool((ext.get("compound_number") or "").strip()),
        "frequency_shown": bool((ext.get("frequency_text") or "").strip()),
        "solvent_shown": bool((ext.get("solvent_text") or "").strip()),
        "integrals_shown": bool(ext.get("integral_values")),
        "peak_labels_shown": bool(ext.get("peak_labels_printed")),
        "insets_present": bool(ext.get("insets")),
        "legibility": ext.get("legibility", "good"),
        "window_left_ppm": None, "window_right_ppm": None, "window_deviation_ppm": None,
        "impurity_labels_on_page": [a["text"].strip() for a in ext.get("annotations", [])],
        "sm_labeled": any(SM_WORDS.match(a["text"].strip()) for a in ext.get("annotations", [])),
        "purity_estimable": False,
    }
    for k in ("tallest_peak_class", "tallest_peak_fraction", "tallest_peak_clipped", "tallest_product_peak_fraction",
              "residual_solvent_ratio", "water_ratio", "grease_ratio", "purity_mol_pct_low", "purity_mol_pct_high",
              "purity_excl_solvents_mol_pct_low", "purity_excl_solvents_mol_pct_high", "unknown_h_equiv",
              "unknown_max_single_h_equiv", "sm_h_equiv", "common_solvent_max_equiv", "grease_h_equiv",
              "integral_includes_solvent_or_water", "calibration_offset_ppm", "baseline_noise_fraction",
              "baseline_drift_fraction", "linewidth_hz", "c13_weakest_snr", "relaxation_delay_s"):
        feats[k] = None
    vals = list(ext.get("integral_values") or [])
    feats["integral_nonint_count"] = sum(1 for v in vals if v >= 0.5 and abs(v - round(v)) > 0.15)
    feats["possible_minor_isomer"] = sum(1 for v in vals if 0.05 <= v <= 0.4) >= 2
    for k in ("ctx_high_complexity", "ctx_small_sample", "ctx_unstable", "ctx_isomers_reported",
              "ctx_low_purity_reason_stated", "ctx_journal", "ctx_journal_requires_freq_solvent"):
        feats[k] = (ctx or {}).get(k)
    evidence = {"solvent": normalize_solvent(ext.get("solvent_text")), "solvent_source": "printed" if ext.get("solvent_text") else "unknown",
                "digitization_error": reason, "signals": []}
    return feats, evidence


def r1(x):
    return None if x is None else round(float(x), 1)


def r3(x):
    return None if x is None else round(float(x), 3)
