# Report maintenance

These tools stay outside the course submission. Run from the repository root:

```sh
python3 tools/verify.py
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/report.py
```

Report generation requires ReportLab, Fontconfig and installed Arial fonts.
The generated report embeds Arial; viewing it needs no extra fonts.
The report reads each part's saved results from `code-a3/pN/results/`.
