import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(r"c:\Users\Shrey\Desktop\TUF_F15_Data\Shrey_academics\MINOR\Attempt_2\synthetic-supervised-parser")

KEYWORD_REGEX = re.compile(r"\b(University|Institute|College|School|IIT|NIT|IIIT|IIM|Vishwavidhyalay|Vishwavidyalaya|Center|Centre)\b", re.IGNORECASE)
NOISE_PREFIX_REGEX = re.compile(r"^(?:degree|board|university|passed|examination|working\s+as|appeared\s+from|\d{4}|\bph\.?d\.?\b|\bdoctor\s+of\s+philosophy\b|\bm\.?tech\.?\b|\bb\.?tech\.?\b|\bdepartment\s+of\s+[\w\s]+\s+(?:at|in)\s+|\bat\s+the\s+|\bat\s+)+", re.IGNORECASE)

def clean_institution_span(line: str) -> str:
    if re.search(r"\b(degree|board)\s+(university|school)\b", line, re.IGNORECASE):
        return ""
    m = KEYWORD_REGEX.search(line)
    if not m:
        return ""
    
    st, en = m.start(), m.end()
    pre = line[:st]
    pre_words = pre.split()
    cand_words = []
    for w in reversed(pre_words):
        w_clean = w.strip(":,.-()")
        if w_clean.istitle() or w_clean.lower() in ("of", "and", "&", "for", "the", "de") or w_clean.isupper():
            cand_words.insert(0, w)
        else:
            break
            
    inst_str = " ".join(cand_words) + " " + line[st:]
    inst_str = re.split(r"[,;\n]|\b(?:in|year|\d{4}|since|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", inst_str, flags=re.IGNORECASE)[0]
    inst_str = NOISE_PREFIX_REGEX.sub("", inst_str.strip()).strip(" :-–—|•●■□*➢ ")
    
    if len(inst_str) < 4 or inst_str.lower() in ("university", "degree university", "institute"):
        return ""
    return inst_str

sec_f = PROJECT_ROOT / "output" / "sections" / "Afzal_Beg_Resume_sections.json"
sec_data = json.load(open(sec_f, encoding="utf-8")).get("sections", {})
for line in sec_data.get("experience", "").splitlines():
    if not line.strip(): continue
    cleaned = clean_institution_span(line)
    print("Raw:    ", line.strip())
    print("Cleaned:", cleaned, "\n")
