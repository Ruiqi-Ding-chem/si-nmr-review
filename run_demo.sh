#!/bin/sh
# Grades the 13 example spectra with both rule sets and opens the report.
cd "$(dirname "$0")" || exit 1
PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
$PY -c "import numpy, scipy, PIL" 2>/dev/null || $PY -m pip install -r requirements.txt
$PY si-nmr-review/scripts/review_images.py examples/images examples/transcriptions demo_output/strict --rubric si-nmr-review/config/rubric.json
$PY si-nmr-review/scripts/review_images.py examples/images examples/transcriptions demo_output/relaxed --rubric si-nmr-review/config/rubric.relaxed.json
$PY si-nmr-review/scripts/report_html.py demo_output/report.html "Strict rules=demo_output/strict" "Relaxed rules=demo_output/relaxed"
(command -v open >/dev/null && open demo_output/report.html) || (command -v xdg-open >/dev/null && xdg-open demo_output/report.html) || echo "Open demo_output/report.html"
