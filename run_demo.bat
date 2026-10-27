@echo off
rem Grades the 13 example spectra with both rule sets and opens the report. Double-click to run.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% -c "import numpy, scipy, PIL" 2>nul || %PY% -m pip install -r requirements.txt
%PY% si-nmr-review\scripts\review_images.py examples\images examples\transcriptions demo_output\strict --rubric si-nmr-review\config\rubric.json
%PY% si-nmr-review\scripts\review_images.py examples\images examples\transcriptions demo_output\relaxed --rubric si-nmr-review\config\rubric.relaxed.json
%PY% si-nmr-review\scripts\report_html.py demo_output\report.html "Strict rules=demo_output\strict" "Relaxed rules=demo_output\relaxed"
start "" demo_output\report.html
