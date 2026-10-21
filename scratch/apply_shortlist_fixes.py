"""Fixes for shortlisting inputs: (A) 'Work History' heading -> experience, (B) name line with a contact tail,
(C) experience stubs with neither title nor institution are not jobs. Asserts each anchor appears exactly once."""
from pathlib import Path

# ---- A. heading map ----
cfg = Path("config/section_normalization_map.json")
c = cfg.read_text(encoding="utf-8")
anchor = '    "employment",\n    "work experience",\n'
assert c.count(anchor) == 1, "config anchor count %d" % c.count(anchor)
c = c.replace(anchor, '    "employment",\n    "work history",\n    "employment history",\n    "work experience",\n')
cfg.write_text(c, encoding="utf-8")

# ---- B + C. Stage 3 ----
path = Path("src/extract_structured_information.py")
src = path.read_text(encoding="utf-8")

def swap(old, new):
    global src
    assert src.count(old) == 1, "anchor count %d for: %s" % (src.count(old), old[:70])
    src = src.replace(old, new)

swap('                line = line.strip()\n                if not line or "@" in line or "http" in line:\n                    continue\n',
     '                line = line.strip()\n'
     '                cut = re.split(r"\\s+[*|\\u2022]\\s+|\\s+\\+?\\d{2,}", line)[0].strip()\n'
     '                if len(cut.split()) >= 2:\n'
     '                    line = cut                          # drop a phone/contact tail so it cannot veto the name\n'
     '                if not line or "@" in line or "http" in line:\n'
     '                    continue\n')

swap('        title_m = TITLE_REGEX.search(entry_text)\n        institution = extract_institution(entry_text)\n        entries.append({\n',
     '        title_m = TITLE_REGEX.search(entry_text)\n        institution = extract_institution(entry_text)\n'
     '        if not title_m and not institution:\n'
     '            continue                                    # stub (e.g. a course line with a year range): not a usable job\n'
     '        entries.append({\n')

path.write_text(src, encoding="utf-8")
print("patched OK")
