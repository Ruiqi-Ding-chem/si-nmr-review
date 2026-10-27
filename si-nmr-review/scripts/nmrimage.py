"""Digitize a raster 1D NMR spectrum image (MestReNova/TopSpin screenshot or a scan).

Everything here is deterministic pixel work. Printed text that needs reading
(axis label values, integral values) comes from the transcription JSON, and is
only matched to positions here.

Output of digitize(): pixel->ppm map, plot extent, baseline, height of the trace
above the baseline for every pixel column, integral bracket regions, and masks
for drawing an overlay.
"""
import numpy as np
from PIL import Image
from scipy import ndimage


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.int16)


def _masks(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    return {
        "white": mn > 205,
        "blue": (b - np.maximum(r, g)) > 40,
        "green": (g - np.maximum(r, b)) > 30,
        "green_soft": (g - np.maximum(r, b)) > 12,
        "blue_soft": (b - np.maximum(r, g)) > 20,
        "gray_dark": (mx < 140) & ((mx - mn) < 45),
        "sat": mx - mn,
        "minv": mn,
        "maxv": mx,
    }


def _longest_run(row_bool):
    """Length, start and end of the longest run of True in a 1D boolean array."""
    if not row_bool.any():
        return 0, 0, 0
    d = np.diff(np.concatenate([[0], row_bool.astype(np.int8), [0]]))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    i = int(np.argmax(ends - starts))
    return int(ends[i] - starts[i]), int(starts[i]), int(ends[i])


def _close_gaps(b, gap=3):
    """Fill runs of False no longer than `gap` that sit between True values (broken scanned lines)."""
    b = b.copy()
    idx = np.where(b)[0]
    if idx.size < 2:
        return b
    for a0, a1 in zip(idx[:-1], idx[1:]):
        if 1 < a1 - a0 <= gap + 1:
            b[a0:a1] = True
    return b


def find_axis(m, W):
    """Lowest long gray horizontal line that has label text under it = the ppm axis."""
    H = m["minv"].shape[0]
    gray = (m["maxv"] < 190) & (m["sat"] < 45)
    for y in range(H - 2, H // 3, -1):
        band = _close_gaps(gray[y - 1:y + 2].any(0))
        n, x0, x1 = _longest_run(band)
        if n > 0.5 * W:
            # settle on the darkest row of the 3-row band, then require labels underneath
            rows = [y - 1, y, y + 1]
            yy = rows[int(np.argmax([gray[r, x0:x1].sum() for r in rows]))]
            clusters, _ = label_clusters(m, yy, x0, x1)
            if len(clusters) >= 3:
                return yy, x0, x1
    # scans: the axis may be a broken line; take the lowest row dense in dark pixels with labels below
    dark = m["minv"] < 200
    for y in range(H - 2, H // 3, -1):
        cnt = dark[y].sum()
        if cnt > 0.25 * W:
            rows = [r for r in (y - 1, y, y + 1) if r < H]
            yy = rows[int(np.argmax([dark[r].sum() for r in rows]))]
            xs = np.where(dark[yy])[0]
            clusters, _ = label_clusters(m, yy, int(xs.min()), int(xs.max()))
            if len(clusters) >= 3:
                return yy, int(xs.min()), int(xs.max())
    raise RuntimeError("x-axis line not found")


def label_clusters(m, axis_y, x0, x1):
    """Centres (x) of the printed axis labels below the axis line."""
    H = m["gray_dark"].shape[0]
    y_lo, y_hi = axis_y + 2, min(H, axis_y + 70)
    ink = (m["sat"][y_lo:y_hi] < 80) & ~m["white"][y_lo:y_hi]
    ink[:, :max(0, x0 - 12)] = False
    ink[:, x1 + 12:] = False
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    comps = []
    for sl in ndimage.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        top = sl[0].start
        if h > 30 or w > 40:
            continue
        if w <= 2 and h >= 3 and top < 4:   # tick mark hanging from the axis
            continue
        comps.append([sl[1].start, sl[1].stop, top, top + h])
    if not comps:
        return [], None
    # the label text row = the row band holding the most tall (digit-sized) components
    tall = [c for c in comps if c[3] - c[2] >= 5]
    if not tall:
        return [], None
    centres = np.array([(c[2] + c[3]) / 2 for c in tall])
    row = int(np.bincount(np.round(centres).astype(int)).argmax())
    char_h = float(np.median([c[3] - c[2] for c in tall if abs((c[2] + c[3]) / 2 - row) <= 4]))
    comps = [c for c in comps if c[2] <= row + char_h * 0.7 and c[3] >= row - char_h * 0.7]
    comps.sort()
    gaps = np.array([b[0] - a[1] for a, b in zip(comps, comps[1:])], float)
    thr = 0.6 * char_h
    if len(gaps) > 3:
        t_otsu = _otsu(gaps)
        lo_c, hi_c = gaps[gaps <= t_otsu], gaps[gaps > t_otsu]
        if lo_c.size and hi_c.size and lo_c.mean() < 0.5 * hi_c.mean() and hi_c.min() - lo_c.max() >= 3:
            thr = t_otsu
    groups, cur = [], [comps[0]]
    for g, c in zip(gaps, comps[1:]):
        if g <= thr:
            cur.append(c)
        else:
            groups.append(cur)
            cur = [c]
    groups.append(cur)
    xs = [((g[0][0] + max(c[1] for c in g) - 1) / 2, g[0][0], max(c[1] for c in g)) for g in groups]
    return xs, y_lo + row


def _otsu(v):
    """Threshold splitting 1D values into two classes with minimum within-class variance."""
    v = np.sort(v)
    best, thr = None, v.mean()
    for i in range(1, len(v)):
        a, b = v[:i], v[i:]
        w = a.var() * len(a) + b.var() * len(b)
        if best is None or w < best:
            best, thr = w, (v[i - 1] + v[i]) / 2
    return thr


def snap_to_ticks(m, axis_y, clusters):
    """Move each label-group centre onto the longest tick mark hanging under the axis near it."""
    H, W = m["minv"].shape
    dark = m["minv"][axis_y + 1:min(H, axis_y + 14)] < 200
    length = np.zeros(W, int)
    for x in range(W):
        col = dark[:, x]
        n = 0
        while n < len(col) and col[n]:
            n += 1
        length[x] = n
    if length.max() < 2:
        return clusters, 0
    cx = [c[0] for c in clusters]
    dx = np.median(np.diff(cx)) if len(cx) > 1 else 20
    out, n_snapped = [], 0
    for c in clusters:
        lo, hi = int(max(0, c[0] - 0.3 * dx)), int(min(W, c[0] + 0.3 * dx + 1))
        seg = length[lo:hi]
        if seg.size and seg.max() >= 3:
            best = np.where(seg == seg.max())[0]
            # a tick may be 2 px wide; take the centre of the longest run
            x = lo + (best.min() + best.max()) / 2 if best.max() - best.min() <= 2 else lo + best[np.argmin(np.abs(lo + best - c[0]))]
            out.append((float(x), c[1], c[2]))
            n_snapped += 1
        else:
            out.append(c)
    return out, n_snapped


def fit_axis(clusters, labels):
    """Match label clusters to the transcribed label values; return (a, b) with ppm = a + b*x."""
    labels = list(labels)
    cx = np.array([c[0] for c in clusters])
    wd = np.array([c[2] - c[1] for c in clusters], float)
    if len(cx) < 2 or len(labels) < 2:
        raise RuntimeError("not enough axis labels to calibrate")
    dx = np.median(np.diff(cx))
    ref = cx[len(cx) // 2]
    t = np.round((cx - ref) / dx).astype(int)
    keep = np.abs(cx - (ref + t * dx)) < 0.3 * dx
    cx, t, wd = cx[keep], t[keep], wd[keep]
    span = t.max() - t.min() + 1
    notes = []
    k = -t.min()
    if span == len(labels) + 1:
        # one extra text group at an end (a clipped label, "ppm", ...): drop the end that is not a full label
        med_w = np.median(wd)
        w_left, w_right = wd[t == t.min()].max(), wd[t == t.max()].max()
        if w_left < 0.85 * med_w <= w_right:
            k, drop = -(t.min() + 1), "left"
        elif w_right < 0.85 * med_w <= w_left:
            drop = "right"
        else:
            raise RuntimeError("axis calibration ambiguous: one label group too many and neither end looks clipped")
        notes.append(f"one extra text group at the {drop} end of the axis was ignored")
    elif span < len(labels):
        raise RuntimeError(f"axis calibration ambiguous: {span} label positions for {len(labels)} transcribed labels")
    elif span != len(labels):
        notes.append(f"{span} label groups found for {len(labels)} transcribed labels; matched from the left")
    idx = t + k
    ok = (idx >= 0) & (idx < len(labels))
    xs, vs = cx[ok], np.array(labels, float)[idx[ok]]
    b, a = np.polyfit(xs, vs, 1)
    resid_px = np.abs((vs - (a + b * xs)) / b)
    for _ in range(2):
        if resid_px.max() <= 1.5 or len(xs) <= 4:
            break
        j = int(np.argmax(resid_px))
        notes.append(f"label {vs[j]:g} dropped from the fit ({resid_px[j]:.1f} px off)")
        xs, vs = np.delete(xs, j), np.delete(vs, j)
        b, a = np.polyfit(xs, vs, 1)
        resid_px = np.abs((vs - (a + b * xs)) / b)
    return a, b, float(resid_px.max()), int(len(xs)), notes


def find_baseline_row(m, axis_y, x0, x1):
    """First long run of trace ink above the axis (the integrals sit in between), else the longest."""
    ink = (m["minv"] < 170) & ~m["blue"] & ~m["green"]
    width = x1 - x0
    best, best_n = None, 0
    for y in range(axis_y - 4, 5, -1):
        band = _close_gaps(ink[y - 1:y + 2, x0:x1].any(0), gap=4)
        n, s, e = _longest_run(band)
        if n > 0.45 * width:
            best, best_n = y, n
            break
        if n > best_n:
            best, best_n = y, n
    rows = [best - 1, best, best + 1]
    counts = [ink[r, x0:x1].sum() for r in rows]
    return rows[int(np.argmax(counts))], best_n


def trace_ink(a, trace_rgb, min_frac=0.15, min_cos=0.985):
    """Pixels whose ink (255 - colour) points the same way as the trace ink.

    Anti-aliased edges of a 1-px line are blends of the trace colour with white, so
    their ink is parallel to the trace ink and they are kept; gray frame lines, blue
    labels and green integrals point elsewhere and are dropped. For a black or gray
    trace every gray pixel passes, and the connectivity step does the filtering.
    """
    v = 255.0 - a
    t = 255.0 - np.asarray(trace_rgb, float)
    tn = np.sqrt((t * t).sum())
    vn = np.sqrt((v * v).sum(-1)) + 1e-9
    cos = (v * t).sum(-1) / (vn * tn)
    return (vn / tn > min_frac) & (cos > min_cos)


def find_plot_top(m, base_y, ax0, ax1):
    """Top of the plot area: a long horizontal frame line above the baseline, or the top end of a
    vertical frame/intensity-axis line at either end of the x-axis. 0 when the plot runs to the image top."""
    gray = (m["maxv"] < 190) & (m["sat"] < 45)
    width = ax1 - ax0
    cands = []
    for y in range(0, max(0, base_y - 40)):
        if _longest_run(gray[y, ax0:ax1])[0] > 0.5 * width:
            cands.append(y)
            break
    H, W = gray.shape
    for x in list(range(max(0, ax0 - 25), ax0 + 3)) + list(range(max(0, ax1 - 3), min(W, ax1 + 25))):
        n, y0, y1 = _longest_run(gray[:base_y + 1, x])
        if n > 0.6 * base_y and y1 >= base_y - 15:
            cands.append(y0)
    return int(min(cands)) if cands else 0


def bridge_label_gaps(trace, ink, max_gap=10):
    """Close short vertical breaks in the trace where a coloured label line crosses a peak."""
    out = trace.copy()
    H, W = trace.shape
    for x in range(W):
        col = trace[:, x]
        ys = np.where(col)[0]
        if ys.size < 2:
            continue
        jumps = np.where(np.diff(ys) > 1)[0]
        for j in jumps:
            y0, y1 = ys[j] + 1, ys[j + 1]
            if y1 - y0 <= max_gap and ink[y0:y1, x].all():
                out[y0:y1, x] = True
    return out


def value_label_boxes(m, base_y, axis_y, xl, xr):
    """Boxes (x0, x1, y0, y1, in plot-relative x) of rotated integral value labels under the baseline."""
    ink = ~m["white"][base_y + 3:axis_y - 2, xl:xr + 1]
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    boxes = [sl for sl in ndimage.find_objects(lab) if sl is not None]
    comps = sorted(((sl[1].start + sl[1].stop) / 2, sl[1].start, sl[1].stop, sl[0].start, sl[0].stop) for sl in boxes
                   if (sl[1].stop - sl[1].start) <= 18)
    groups = []
    for c in comps:
        if groups and abs(c[0] - groups[-1][0]) <= 4:
            g = groups[-1]
            members = g[5] + 1
            groups[-1] = ((g[0] * g[5] + c[0]) / members, min(g[1], c[1]), max(g[2], c[2]), min(g[3], c[3]), max(g[4], c[4]), members)
        else:
            groups.append(c + (1,))
    return [(g[1], g[2], g[3], g[4]) for g in groups if (g[4] - g[3]) >= 12 and (g[2] - g[1]) <= 18]


def merge_unlabelled(regions, centres, n_expected):
    """Merge touching bracket pieces until there are n_expected regions.

    With one value label per expected region, choose the merges that put each label (in order) over
    its region; give up (return None) if some label then sits far from its region, because the pieces
    are then not the author's brackets. With fewer labels found, merge the narrowest piece into its
    narrower touching neighbour, one at a time (a value-label leader touching a bracket line makes a
    short false piece)."""
    from itertools import combinations
    regions = list(regions)
    extra = len(regions) - n_expected
    if extra <= 0:
        return regions
    joins = [i for i in range(len(regions) - 1) if abs(regions[i][1] - regions[i + 1][0]) <= 3]
    if len(centres) == n_expected:
        best, best_cost, best_worst = None, None, None
        for combo in combinations(joins, extra):
            merged, cur = [], list(regions[0])
            for i in range(1, len(regions)):
                if (i - 1) in combo:
                    cur[1] = regions[i][1]
                else:
                    merged.append(tuple(cur))
                    cur = list(regions[i])
            merged.append(tuple(cur))
            d = [abs((r0 + r1) / 2 - c) - 0.5 * (r1 - r0) for (r0, r1), c in zip(merged, sorted(centres))]
            cost = sum(max(0.0, x) for x in d)
            if best_cost is None or cost < best_cost:
                best, best_cost, best_worst = merged, cost, max(d)
        if best is None or best_worst > 8:
            return None
        return best
    while len(regions) > n_expected:
        cand = [(r[1] - r[0], i) for i, r in enumerate(regions)
                if (i - 1 in joins) or (i in joins)]
        if not cand:
            return None
        _, i = min(cand)
        nbrs = [j for j in (i - 1, i + 1) if 0 <= j < len(regions) and min(i, j) in joins]
        j = min(nbrs, key=lambda k: regions[k][1] - regions[k][0])
        a, b = sorted((i, j))
        regions[a] = (regions[a][0], regions[b][1])
        del regions[b]
        joins = [k for k in range(len(regions) - 1) if abs(regions[k][1] - regions[k + 1][0]) <= 3]
    return regions


def value_label_regions(m, h, base_y, axis_y, xl, xr, n_expected):
    """Fallback: x-centres of the integral value labels (rotated numbers) under the baseline,
    each turned into the signal cluster of the trace right above it."""
    labels = value_label_boxes(m, base_y, axis_y, xl, xr)
    if len(labels) != n_expected:
        return None
    centres = [(g[0] + g[1]) / 2 for g in labels]
    active = h > 1.5
    regions = []
    for i, c in enumerate(centres):
        c = int(round(c))
        j = c
        if not active[min(max(j, 0), len(h) - 1)]:
            near = np.where(active[max(0, c - 10):c + 11])[0]
            if near.size == 0:
                regions.append((xl + c - 2, xl + c + 2))
                continue
            j = max(0, c - 10) + int(near[np.argmin(np.abs(near + max(0, c - 10) - c))])
        # walk out from the signal under the label; stop at the baseline or at a deep valley
        # (below 30% of the tallest line met so far), which separates a neighbouring signal
        a0, top_l = j, h[j]
        while a0 > 0 and active[a0 - 1]:
            top_l = max(top_l, h[a0 - 1])
            if h[a0 - 1] < 0.3 * top_l and a0 - 2 >= 0 and h[a0 - 2] > h[a0 - 1]:
                break
            a0 -= 1
        a1, top_r = j, h[j]
        while a1 < len(h) - 1 and active[a1 + 1]:
            top_r = max(top_r, h[a1 + 1])
            if h[a1 + 1] < 0.3 * top_r and a1 + 2 < len(h) and h[a1 + 2] > h[a1 + 1]:
                break
            a1 += 1
        # neighbouring labels over one cluster split it at the midpoint
        if i > 0:
            a0 = max(a0, int((centres[i - 1] + centres[i]) / 2) + 1)
        if i < len(centres) - 1:
            a1 = min(a1, int((centres[i] + centres[i + 1]) / 2))
        regions.append((xl + a0, xl + a1))
    return regions


def digitize(path, axis_labels, plot_top=None, n_integrals=None):
    a = load_rgb(path)
    H, W, _ = a.shape
    m = _masks(a)
    axis_y, ax0, ax1 = find_axis(m, W)
    clusters, label_row = label_clusters(m, axis_y, ax0, ax1)
    # labels clipped by the image border are not in the transcription (it lists fully printed labels only)
    widths = np.array([c[2] - c[1] for c in clusters]) if clusters else np.array([])
    keep = [c for c in clusters if not ((c[1] <= 1 or c[2] >= W - 2) and (c[2] - c[1]) < 0.85 * np.median(widths))]
    n_clipped = len(clusters) - len(keep)
    clusters = keep
    clusters, n_snapped = snap_to_ticks(m, axis_y, clusters)
    ca, cb, resid, n_used, notes = fit_axis(clusters, axis_labels)
    notes = notes + [f"{n_snapped} of {len(clusters)} labels snapped to tick marks"] + (
        [f"{n_clipped} label(s) clipped by the image border ignored"] if n_clipped else [])
    step = abs(axis_labels[0] - axis_labels[1]) if len(axis_labels) > 1 else 1.0
    lo_v, hi_v = ca + cb * ax1, ca + cb * ax0
    if not (hi_v >= max(axis_labels) - 0.6 * step and lo_v <= min(axis_labels) + 0.6 * step and resid <= 2.0):
        raise RuntimeError(f"axis calibration failed: axis spans {hi_v:.2f} to {lo_v:.2f} ppm, labels run "
                           f"{max(axis_labels):g} to {min(axis_labels):g}; residual {resid:.1f} px")

    base_y, base_run = find_baseline_row(m, axis_y, ax0, ax1)
    row = a[base_y, ax0:ax1]
    keep = (m["minv"][base_y, ax0:ax1] < 170) & ~m["blue"][base_y, ax0:ax1] & ~m["green"][base_y, ax0:ax1]
    trace_rgb = np.median(row[keep], axis=0)
    trace = trace_ink(a, trace_rgb) & ~m["blue"] & ~m["green"]
    trace[axis_y - 1:, :] = False
    # erase long horizontal lines away from the baseline (plot frame, inset baselines)
    # (a baseline that steps a little over part of the window stays)
    for y in range(trace.shape[0]):
        if abs(y - base_y) > max(4, 0.05 * H) and _longest_run(trace[y])[0] > 0.3 * (ax1 - ax0):
            trace[y] = False
    if plot_top is None:
        plot_top = find_plot_top(m, base_y, ax0, ax1)

    trace = bridge_label_gaps(trace, ~m["white"])
    lab, _ = ndimage.label(trace, structure=np.ones((3, 3)))
    band = lab[max(0, base_y - 3):base_y + 4, :]
    ids = np.unique(band[band > 0])
    spec = np.isin(lab, ids)

    cols = np.arange(W)
    has = spec.any(0)
    top = np.where(has, spec.argmax(0), -1)
    bottom = np.where(has, H - 1 - spec[::-1].argmax(0), -1)
    has[:ax0 + 1] = False
    has[ax1 - 1:] = False
    xs_valid = cols[has]
    xl, xr = int(xs_valid.min()), int(xs_valid.max())
    bot = bottom.astype(float)
    bot[~has] = np.nan
    s = np.copy(bot[xl:xr + 1])
    s = np.where(np.isnan(s), np.nanmedian(s), s)
    base = ndimage.median_filter(s, size=61, mode="nearest")
    tp = top[xl:xr + 1].astype(float)
    tp = np.where(tp < 0, base, tp)
    raw_h = base - tp
    thick = float(np.median(raw_h[raw_h <= np.percentile(raw_h, 60)]))
    h = np.clip(raw_h - thick, 0, None)
    display = float(np.median(base) - plot_top)
    # a frame line or a vertical intensity axis at the very ends shows up as an isolated spike reaching the top
    spike = np.zeros(len(h), bool)
    for i in list(range(0, min(4, len(h)))) + list(range(max(0, len(h) - 4), len(h))):
        nb = np.concatenate([h[max(0, i - 4):max(0, i - 1)], h[i + 2:i + 5]])
        if h[i] > 0.4 * display and tp[i] <= plot_top + 3 and (len(nb) == 0 or nb.max() < 0.1 * display):
            h[i], spike[i] = 0.0, True
    clipped = (tp <= plot_top + 1) & ~spike

    xpix = np.arange(xl, xr + 1)
    ppm = ca + cb * xpix

    regions = integral_regions(m, int(np.median(base)), axis_y, xl, xr)
    region_source = "brackets"
    if n_integrals and len(regions) > n_integrals:
        boxes = value_label_boxes(m, int(np.median(base)), axis_y, xl, xr)
        centres = [xl + (b0 + b1) / 2 for b0, b1, _, _ in boxes]
        merged = merge_unlabelled(regions, centres, n_integrals)
        if merged is not None:
            regions = merged
            region_source = "brackets (extra pieces merged)"
    if n_integrals and len(regions) != n_integrals:
        alt = value_label_regions(m, h, int(np.median(base)), axis_y, xl, xr, n_integrals)
        if alt is not None:
            regions, region_source = alt, "value labels"
    regions_ppm = [(float(ca + cb * r0), float(ca + cb * r1)) for r0, r1 in regions]

    return {
        "shape": (H, W),
        "axis_y": int(axis_y),
        "axis_fit": {"a": float(ca), "b": float(cb), "max_resid_px": resid, "labels_used": n_used, "notes": notes},
        "label_row": label_row,
        "baseline_row": int(base_y),
        "trace_rgb": [float(v) for v in trace_rgb],
        "x_left": xl, "x_right": xr,
        "window_ppm": (float(ca + cb * xl), float(ca + cb * xr)),
        "ppm": ppm, "h": h, "base": base, "bottom": s, "top": tp, "clipped": clipped,
        "display_px": display, "line_thickness_px": thick, "plot_top": int(plot_top),
        "ppm_per_px": float(abs(cb)),
        "regions_px": regions, "regions_ppm": regions_ppm, "region_source": region_source,
        "spec_mask": spec,
    }


def integral_regions(m, base_y, axis_y, xl, xr):
    """x-ranges of integral brackets drawn between the baseline and the axis.

    A bracket is a horizontal line with a short vertical tick at each end; the leader
    to its value label may cover the middle of the line. Ticks of neighbouring brackets
    can touch, so a tick cluster may close one bracket and open the next. Brackets are
    green in most MestReNova exports; blue and black ones are tried next.
    """
    for key in ("green", "blue", "ink"):
        mask = (~m["white"]) if key == "ink" else m[key + "_soft"]
        regions = _brackets(mask, m["white"], base_y, axis_y, xl, xr)
        if len(regions) >= 1:
            return regions
    return []


def _brackets(mask, white, base_y, axis_y, xl, xr):
    g = mask[base_y + 3:axis_y - 2, :].copy()
    g[:, :max(0, xl - 2)] = False
    g[:, xr + 3:] = False
    if g.sum() < 10:
        return []
    runs = np.zeros(g.shape[0])
    for y in range(g.shape[0]):
        d = np.diff(np.concatenate([[0], g[y].astype(np.int8), [0]]))
        st, en = np.where(d == 1)[0], np.where(d == -1)[0]
        runs[y] = sum(e - s0 for s0, e in zip(st, en) if e - s0 >= 4)
    if runs.max() < 8:
        return []
    yb = int(runs.argmax())
    band = g[max(0, yb - 4):yb + 5]
    counts = band.sum(0)
    on_line = counts[g[yb]] if g[yb].any() else counts[counts > 0]
    line_th = int(np.median(on_line)) if on_line.size else 1
    tick = counts >= line_th + 2
    cols = np.where(tick)[0]
    if len(cols) < 2:
        return []
    clusters, cur = [], [cols[0]]
    for c in cols[1:]:
        if c - cur[-1] <= 1:
            cur.append(c)
        else:
            clusters.append((cur[0], cur[-1]))
            cur = [c]
    clusters.append((cur[0], cur[-1]))
    line = ~white[base_y + 3 + yb]
    regions = []
    for (a0, a1), (b0, b1) in zip(clusters, clusters[1:]):
        inner = np.arange(a1 + 1, b0)
        if len(inner) < 2:
            continue
        if line[inner].mean() >= 0.7 and g[yb, inner].mean() >= 0.4:
            regions.append((int((a0 + a1) // 2), int((b0 + b1 + 1) // 2)))
    return regions
