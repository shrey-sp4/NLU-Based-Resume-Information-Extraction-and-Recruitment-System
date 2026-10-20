import json, re
from pathlib import Path

names = ["Snehamoy_P_CV", "Curriculum_Vitae_Rakesh", "Updated_CV-_Dr_Soumen_Mukherjee"]
kw = re.compile(r"publication|journal|conference|paper|proceeding|research|achievement|award", re.I)
out = []
for n in names:
    out.append("=== " + n)
    txt = Path("data/real_resumes/extracted_text/" + n + ".txt")
    if txt.exists():
        for i, line in enumerate(txt.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if 2 < len(s) <= 60 and kw.search(s):
                out.append("  line %d: %s" % (i, s))
    sec = Path("output/sections/" + n + "_sections.json")
    if sec.exists():
        d = json.loads(sec.read_text(encoding="utf-8"))
        for b in d.get("boundaries", []):
            out.append("  BOUNDARY " + json.dumps(b, ensure_ascii=True)[:200])
        for g in d.get("ignored_headings", []):
            out.append("  IGNORED  " + json.dumps(g, ensure_ascii=True)[:200])
text = "\n".join(out).encode("ascii", "replace").decode("ascii")
Path("scratch/heading_probe.txt").write_text(text, encoding="ascii")
print("written scratch/heading_probe.txt")
