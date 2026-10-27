"""One self-contained HTML page from one or more pipeline output folders.

    python report_html.py <out.html> "<label>=<output_dir>" ["<label>=<output_dir>" ...]

Each output folder is what review_images.py wrote (NAME_grade.json, NAME_features.json,
NAME_overlay.png). With several folders (for example the strict and the relaxed rubric) the
grades sit side by side; the overlays and measurements come from the first folder.
"""
import base64
import glob
import html
import json
import os
import sys

COLORS = {"N": "#E48A8A", "S-": "#F9E3C2", "S": "#F2C788", "S+": "#E8A23F", "V-": "#C4E7DB",
          "V": "#86CDB6", "V+": "#3FAE8C", "E-": "#A9CBEE", "E": "#5E9BDB"}
ORDER = ["N", "S-", "S", "S+", "V-", "V", "V+", "E-", "E"]


def pill(g):
    g = (g or "").replace("−", "-")
    c = COLORS.get(g, "#DDDDDD")
    return f'<span class="pill" style="background:{c}">{html.escape(g.replace("-", "−"))}</span>'


def load(folder):
    res = {}
    for p in sorted(glob.glob(os.path.join(folder, "*_grade.json"))):
        name = os.path.basename(p)[:-len("_grade.json")]
        with open(p, encoding="utf-8") as f:
            g = json.load(f)
        fp = os.path.join(folder, name + "_features.json")
        fe = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else {"features": {}, "evidence": {}}
        res[name] = {"grade": g, "features": fe["features"], "evidence": fe["evidence"],
                     "overlay": os.path.join(folder, name + "_overlay.png")}
    return res


def img_tag(path, alt):
    if not os.path.exists(path):
        return '<div class="noimg">no overlay (the trace could not be digitized)</div>'
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'<img alt="{html.escape(alt)}" src="data:image/png;base64,{b64}">'


def main():
    out = sys.argv[1]
    runs = []
    for arg in sys.argv[2:]:
        label, folder = arg.split("=", 1)
        runs.append((label, load(folder)))
    names = sorted(runs[0][1])

    rows = []
    for n in names:
        cells = "".join(f"<td>{pill(r[n]['grade']['grade']) if n in r else ''}</td>" for _, r in runs)
        f = runs[0][1][n]["features"]
        pur = ("n/a" if f.get("purity_mol_pct_low") is None
               else f"{f['purity_mol_pct_low']:.0f}–{f['purity_mol_pct_high']:.0f}%")
        rows.append(f'<tr><td><a href="#{n}">{html.escape(n)}</a></td>{cells}<td>{pur}</td></tr>')

    cards = []
    for n in names:
        first = runs[0][1][n]
        ev, f = first["evidence"], first["features"]
        grades = " ".join(f'<span class="lab">{html.escape(lbl)}</span> {pill(r[n]["grade"]["grade"])}' for lbl, r in runs if n in r)
        blocks = []
        for lbl, r in runs:
            g = r[n]["grade"]
            items = "".join(
                f'<li><b>{html.escape(x["title"])}</b> '
                f'<span class="eff">{"−" + format(x["notches"], "g") if x["effect"] == "deduct" else ("max " + x.get("cap", "")) if x["effect"] == "cap" else "flag"}</span>'
                f'<br><span class="why">{html.escape(x["reason"])}</span></li>'
                for x in g["fired"])
            review = "".join(f"<li>{html.escape(h)}</li>" for h in g["human_review"])
            blocks.append(f'<div class="rules"><h4>{html.escape(lbl)}: {pill(g["grade"])}'
                          f' <small>base {html.escape(g["base_grade"])} from purity {g["purity_used"] if g["purity_used"] is not None else "n/a"}</small></h4>'
                          f'<ul>{items or "<li>no rule charged</li>"}</ul>'
                          + (f'<p class="np">Needs a person</p><ul>{review}</ul>' if review else "") + "</div>")
        sig = ", ".join(f'{s["ppm"]:.2f} {s["class"].replace("_", " ")}' for s in ev.get("signals", [])
                        if s["class"] not in ("c13_satellite",))
        meas = []
        if f.get("purity_mol_pct_low") is not None:
            meas.append(f"purity {f['purity_mol_pct_low']:.0f}–{f['purity_mol_pct_high']:.0f} mol%")
        if f.get("tallest_peak_class"):
            meas.append(f"tallest peak: {f['tallest_peak_class'].replace('_', ' ')} at {f['tallest_peak_fraction']:.2f} of height")
        if ev.get("solvent"):
            meas.append(f"solvent {ev['solvent']} ({ev.get('solvent_source', '')})")
        if ev.get("digitization_error"):
            meas.append("trace not digitized: " + ev["digitization_error"])
        cards.append(f'''<section class="card" id="{html.escape(n)}">
<h2>{html.escape(n)} <span class="gr">{grades}</span></h2>
<div class="row"><div class="img">{img_tag(first["overlay"], n + " overlay")}
<p class="cap">Magenta: baseline · orange: integral regions · boxes: signals outside the integrals (red unknown, purple grease, blue water, green residual solvent, orange common solvent, brown starting material)</p></div>
<div class="txt"><p class="meas">{html.escape("; ".join(meas))}</p>
<p class="sig"><b>Signals outside the integrals:</b> {html.escape(sig) or "none"}</p>
{"".join(blocks)}</div></div></section>''')

    head = "".join(f"<th>{html.escape(lbl)}</th>" for lbl, _ in runs)
    legend = " ".join(pill(g) for g in ORDER)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>SI NMR pre-screen</title>
<style>
:root{{--ink:#1C2733;--soft:#3E4A57;--mute:#6A7684;--paper:#F7F5F0;--line:#D9DEE3}}
body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.45 system-ui,Segoe UI,Arial,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}}
h1{{font:600 30px Georgia,serif;margin:8px 0}} h2{{font:600 22px Georgia,serif;margin:0 0 10px}}
table{{border-collapse:collapse;background:#fff;border:1px solid var(--line)}}
td,th{{padding:6px 12px;border-bottom:1px solid var(--line);text-align:left}}
.pill{{display:inline-block;min-width:34px;text-align:center;font-weight:600;padding:2px 8px;border-radius:7px;color:#1C2733}}
.card{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:18px 0}}
.row{{display:flex;gap:18px;flex-wrap:wrap}} .img{{flex:1 1 560px}} .txt{{flex:1 1 380px}}
.img img{{width:100%;height:auto;border:1px solid var(--line);border-radius:8px}}
.cap,.why,small{{color:var(--mute);font-size:13px}} .meas{{font-weight:600}} .lab{{color:var(--mute);font-size:14px;margin-left:10px}}
.rules h4{{margin:12px 0 4px}} ul{{margin:4px 0 8px 18px;padding:0}} .eff{{color:#9A5410;font-weight:600}} .np{{font-weight:600;margin:6px 0 0}}
.noimg{{padding:40px;text-align:center;color:var(--mute);border:1px dashed var(--line);border-radius:8px}}
</style></head><body><main>
<h1>SI NMR pre-screen</h1>
<p>Suggested grades from fixed rules applied to measured features. The final grade is the reviewer’s.</p>
<p>{legend} <small>one colour per letter; + darker, − lighter</small></p>
<table><tr><th>Spectrum</th>{head}<th>Purity (first run)</th></tr>{"".join(rows)}</table>
{"".join(cards)}
</main></body></html>"""
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print(out)


if __name__ == "__main__":
    main()
