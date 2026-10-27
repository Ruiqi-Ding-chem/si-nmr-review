"""Apply a rubric (config/rubric.json) to one spectrum's features.

The algorithm is fixed; the rubric only supplies numbers and rules:
  1. base grade from purity (purity_basis picks the low bound, midpoint or high bound)
  2. every rule whose condition holds fires: deduct notches (summed per group, limited by
     group_max_deduction), cap the grade, or only flag
  3. grade = min(base - deductions, lowest cap), never below N
  4. context modifiers (only when the author supplied ctx_* features) add notches back,
     never above a cap set by a blocker rule
"""
import json
import re

SCALE = ["N", "S-", "S", "S+", "V-", "V", "V+", "E-", "E"]


def norm_grade(g):
    g = (g or "").strip().replace("–", "-").replace("−", "-").upper().replace("E+", "E")
    if g not in SCALE:
        raise ValueError(f"unknown grade {g!r}")
    return g


def idx(g):
    return SCALE.index(norm_grade(g))


OPS = {
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b,
}


def evaluate(cond, f, known, errors):
    if "all" in cond:
        return all(evaluate(c, f, known, errors) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, f, known, errors) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], f, known, errors)
    name, op = cond.get("feature"), cond.get("op")
    if name not in known:
        errors.add(f"unknown feature {name!r}")
        return False
    v = f.get(name)
    if op == "is_null":
        return v is None
    if op == "not_null":
        return v is not None
    if v is None:
        return False
    if op == "is_true":
        return v is True
    if op == "is_false":
        return v is False
    if op not in OPS:
        errors.add(f"unknown op {op!r}")
        return False
    try:
        if isinstance(v, list) and op in ("in", "not_in"):
            hit = any(x in cond["value"] for x in v)
            return hit if op == "in" else not hit
        return OPS[op](v, cond["value"])
    except TypeError:
        errors.add(f"type mismatch on {name} {op} {cond.get('value')!r}")
        return False


def fill(template, f):
    def rep(m):
        name, spec = m.group(1), m.group(2)
        v = f.get(name)
        if v is None:
            return "n/a"
        if isinstance(v, float) and not spec:
            return f"{v:.3g}"
        try:
            return format(v, spec) if spec else str(v)
        except (ValueError, TypeError):
            return str(v)
    return re.sub(r"\{([A-Za-z0-9_]+)(?::([^}]*))?\}", rep, template)


def grade(features, rubric, purity_override=None):
    known = set(features)
    errors = set()
    nuc = features.get("nucleus", "1H")
    lo, hi = features.get("purity_mol_pct_low"), features.get("purity_mol_pct_high")
    basis = rubric.get("purity_basis", "mid")
    if purity_override is not None:
        purity = purity_override
    elif lo is None or hi is None:
        purity = None
    else:
        purity = {"low": lo, "high": hi}.get(basis, (lo + hi) / 2)

    table = sorted(rubric["base_grade_table"], key=lambda r: -r["min_purity_mol_pct"])
    if purity is None or not features.get("purity_estimable", True):
        base = idx(rubric["default_base_grade_if_purity_unknown"])
    else:
        base = 0
        for row in table:
            if purity >= row["min_purity_mol_pct"]:
                base = idx(row["grade"])
                break

    fired, by_group, caps, blocker_caps, review = [], {}, [], [], []
    for r in rubric["rules"]:
        if r.get("nucleus", "any") not in ("any", nuc):
            continue
        if not evaluate(r["condition"], features, known, errors):
            continue
        reason = fill(r["reason_template"], features)
        item = {"id": r["id"], "title": r["title"], "effect": r["effect"], "severity": r["severity"],
                "reason": reason, "standard_quote": r["standard_quote"]}
        if r["effect"] == "deduct":
            n = float(r.get("notches") or 0)
            by_group.setdefault(r.get("group") or r["id"], []).append(n)
            item["notches"] = n
        elif r["effect"] == "cap":
            c = idx(r["cap_grade"])
            caps.append(c)
            if r["severity"] == "blocker":
                blocker_caps.append(c)
            item["cap"] = norm_grade(r["cap_grade"])
        if r.get("human_review"):
            review.append(f"{r['title']}: {reason}")
        fired.append(item)

    gmax = rubric.get("group_max_deduction") or {}
    total = 0.0
    for g, ns in by_group.items():
        t = sum(ns)
        if g in gmax:
            t = min(t, float(gmax[g]))
        total += t
    g_idx = base - total
    if caps:
        g_idx = min(g_idx, min(caps))

    ctx_items = []
    for cm in rubric.get("context_modifiers", []):
        if evaluate(cm["condition"], features, known, errors):
            item = {"id": cm["id"], "effect": cm["effect"], "note": cm["note"]}
            if cm["effect"] == "add":
                # context gives notches back; it never lifts the grade above what purity alone allows
                g_idx = min(g_idx + float(cm.get("notches") or 0), max(g_idx, base))
                item["notches"] = cm.get("notches")
            ctx_items.append(item)
    ceiling = min(blocker_caps) if blocker_caps else len(SCALE) - 1
    g_idx = max(0, min(int(round(g_idx - 1e-9)) if g_idx >= 0 else 0, ceiling, len(SCALE) - 1))

    return {
        "grade": SCALE[g_idx],
        "grade_index": g_idx,
        "base_grade": SCALE[base],
        "purity_used": purity,
        "purity_basis": basis,
        "total_deduction": total,
        "caps": [SCALE[c] for c in caps],
        "fired": fired,
        "context": ctx_items,
        "human_review": review,
        "rubric_errors": sorted(errors),
    }


def grade_with_range(features, rubric):
    """Grade at the rubric's purity basis, plus the grades the low and high purity bounds would give."""
    main = grade(features, rubric)
    lo, hi = features.get("purity_mol_pct_low"), features.get("purity_mol_pct_high")
    if lo is not None and hi is not None and features.get("purity_estimable", True):
        g_lo = grade(features, rubric, purity_override=lo)["grade"]
        g_hi = grade(features, rubric, purity_override=hi)["grade"]
        main["grade_if_purity_low"], main["grade_if_purity_high"] = g_lo, g_hi
    return main


if __name__ == "__main__":
    import sys
    feats = json.load(open(sys.argv[1], encoding="utf-8"))
    rub = json.load(open(sys.argv[2], encoding="utf-8"))
    print(json.dumps(grade_with_range(feats, rub), indent=2, ensure_ascii=False))
