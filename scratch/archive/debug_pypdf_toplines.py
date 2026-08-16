import io
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

pdfs = [
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Doyel-Mukherjee-25.06.2024.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Dibakar_Resume_June_2024.pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Dhwanil G_CV (2024).pdf",
    PROJECT_ROOT / "data" / "real_resumes" / "original" / "Priyanka Sharma_CV.pdf"
]

for p in pdfs:
    reader = pypdf.PdfReader(p)
    txt = reader.pages[0].extract_text() or ""
    lines = [l.strip() for l in txt.splitlines() if l.strip()][:8]
    print(f"=== {p.name} (Top Lines) ===")
    for i, line in enumerate(lines):
        print(f"  [{i+1}] \"{line}\"")
    print("-" * 60)
