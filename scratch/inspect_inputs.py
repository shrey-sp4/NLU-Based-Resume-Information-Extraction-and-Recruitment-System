import json, re
from pathlib import Path

out = []
def lines_of(stem):
    p = Path("data/real_resumes/extracted_text/" + stem + ".txt")
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []

for stem in ["cv_aakash_daiict", "CV_Chandan"]:
    out.append("===== " + stem)
    sp = Path("output/sections/" + stem + "_sections.json")
    if sp.exists():
        d = json.loads(sp.read_text(encoding="utf-8"))
        out.append("sections: " + str(list(d["sections"].keys())))
        out.append("--- experience section text (first 700 chars):")
        out.append((d["sections"].get("experience") or "(none)")[:700])
        out.append("--- boundaries: " + "; ".join("%s@%d" % (b["raw_heading"], b["line_number"]) for b in d["boundaries"]))
    out.append("--- lines mentioning roles or year ranges:")
    for i, l in enumerate(lines_of(stem), 1):
        if re.search(r"scholar|professor|lecturer|fellow|associate|assistant|(?:19|20)\d{2}\s*[-\u2013]\s*(?:(?:19|20)\d{2}|present|till)", l, re.I):
            out.append("  line %d: %s" % (i, l.strip()[:120]))

for stem in ["CV-Anurag_Choudhary", "Dr_Akash_Thakkar_CV"]:
    out.append("===== " + stem + " (first 8 non-empty lines)")
    shown = 0
    for l in lines_of(stem):
        if l.strip():
            out.append("  " + l.strip()[:110]); shown += 1
        if shown == 8:
            break

text = "\n".join(out).encode("ascii", "replace").decode("ascii")
Path("scratch/inspect_inputs.txt").write_text(text, encoding="ascii")
print("written scratch/inspect_inputs.txt")
