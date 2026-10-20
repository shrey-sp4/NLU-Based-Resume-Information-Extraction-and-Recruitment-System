"""Read-only: how many glued (no-space) long words does Stage 1 produce at different pdfplumber x_tolerance values?
Usage: python scratch/spacing_probe.py <folder with the PDFs>
Writes scratch/spacing_probe.txt (UTF-8). Changes nothing else."""
import re, sys
from pathlib import Path
import pdfplumber

folder = Path(sys.argv[1])
settings = [("x_tol=3 (current)", {}), ("x_tol=2", {"x_tolerance": 2}),
            ("x_tol=1.5", {"x_tolerance": 1.5}), ("x_tol=1", {"x_tolerance": 1})]
glued = re.compile(r"[A-Za-z]{22,}")
lines = []
for pdf_path in sorted(folder.glob("*.pdf")):
    row = [pdf_path.name]
    for label, kw in settings:
        n = 0
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                n += len(glued.findall(page.extract_text(**kw) or ""))
        row.append(f"{n}")
    lines.append("\t".join(row))
header = "file\t" + "\t".join(s[0] for s in settings)
Path("scratch/spacing_probe.txt").write_text(header + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
print("done:", len(lines), "pdfs -> scratch/spacing_probe.txt")