"""Name fallback: when no name is found in the preamble, take a name-shaped line within 12 lines of the email
if at least two of its words appear in the email address. Asserts each anchor appears exactly once."""
from pathlib import Path

path = Path("src/extract_structured_information.py")
src = path.read_text(encoding="utf-8")

def swap(old, new):
    global src
    assert src.count(old) == 1, "anchor count %d for: %s" % (src.count(old), old[:70])
    src = src.replace(old, new)

swap("def extract_personal_details(sections):", '''def _name_from_email_context(text, email):
    """Name-shaped line near the email whose words (at least two) appear in the email address; else empty."""
    if not email:
        return ""
    local = re.sub(r"[^a-z]", "", email.split("@")[0].lower())
    lines = [l.strip() for l in text.splitlines()]
    hits = [i for i, l in enumerate(lines) if email in l]
    if not hits:
        return ""
    for l in lines[max(0, hits[0] - 12): hits[0] + 13]:
        if "@" in l or "http" in l:
            continue
        cand = re.sub(r"[^\\w\\s\\.\\-']", " ", re.split(r"\\d", l)[0])
        cand = re.sub(r"\\s+", " ", cand).strip()
        if 2 <= len(cand.split()) <= 5 and re.match(r"^[A-Za-z\\.\\s\\-']+$", cand) and _name_shape_ok(cand):
            words = [w for w in re.findall(r"[a-z]+", cand.lower()) if len(w) >= 3 and w not in _NAME_TITLES and w not in _NAME_SUFFIXES]
            if sum(w in local for w in words) >= 2:
                return cand
    return ""

def extract_personal_details(sections):''')

swap('        name = _pick_name(name_candidates, email)\n\n    return {"name": name,',
     '        name = _pick_name(name_candidates, email)\n\n    if not name:\n        name = _name_from_email_context(full_doc_text, email)\n\n    return {"name": name,')

path.write_text(src, encoding="utf-8")
print("patched OK")
