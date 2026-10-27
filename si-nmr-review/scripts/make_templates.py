"""Write a blank transcription file for every spectrum image, for filling in by hand.

    python make_templates.py <images_dir> <transcriptions_dir>

Existing files are left alone. Only two fields are needed for a grade: axis_labels and
integral_values; the others refine the presentation checks. axis_labels may be written
as a range, for example "11 to -1 step 0.5".
"""
import json
import os
import sys

IMG_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")

TEMPLATE = {
    "_help": ("Fill axis_labels (the numbers printed under the x-axis, left to right, or a range such as "
              "'11 to -1 step 0.5') and integral_values (the printed integrals from highest ppm to lowest). "
              "Fill the rest if the page shows it: compound_number, frequency_text and solvent_text exactly "
              "as printed, structure_drawn true/false, annotations such as {\"text\": \"EtOAc\", \"approx_ppm\": 2.05}, "
              "legibility good/fair/poor."),
    "axis_labels": "",
    "integral_values": [],
    "compound_number": "",
    "frequency_text": "",
    "solvent_text": "",
    "structure_drawn": False,
    "peak_labels_printed": True,
    "annotations": [],
    "insets": [],
    "legibility": "good",
    "title_lines": [],
    "structure_location": "none",
    "integral_style": "brackets below baseline",
    "vertical_intensity_axis": False,
    "image_kind": "software screenshot",
    "trace_color": "",
    "notes": "",
}


def main():
    images, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    made = 0
    for fn in sorted(os.listdir(images)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in IMG_EXT:
            continue
        path = os.path.join(out, stem + ".json")
        if os.path.exists(path):
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(TEMPLATE, f, indent=2)
        made += 1
    print(f"{made} template(s) written to {out}")


if __name__ == "__main__":
    main()
