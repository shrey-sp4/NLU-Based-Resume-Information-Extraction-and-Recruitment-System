"""Stage 3 publication cleanup 2: count/label lines, bare sub-heading entries, split after author initial, glued 'Chaptersin'.
Asserts each anchor appears exactly once."""
from pathlib import Path

path = Path("src/extract_structured_information.py")
src = path.read_text(encoding="utf-8")

def swap(old, new):
    global src
    assert src.count(old) == 1, "anchor count %d for: %s" % (src.count(old), old[:60])
    src = src.replace(old, new)

# 1. helpers (before the non-citation check)
swap("def _is_non_citation_entry(entry):", '''_COUNT_LABEL = re.compile(r"^\\s*[A-Za-z/&() \\-]{6,90}:\\s*\\d{1,3}\\b(?:\\s+[A-Z][A-Z&/-]+(?=\\s|$)){0,6}")
_BARE_LABEL = re.compile(
    r"[\\W_]*(?:(?:journals?|conferences?|papers?|articles?|publications?|proceedings?|international|national|"
    r"refereed|peer|reviewed|and|in|of|the)[\\W_]*)+", re.IGNORECASE)

def _strip_count_label(entry):
    """'Conference Paper Published in X: 59 PAPER IN PROCEEDING BOOK S. Karmakar, ...' -> 'S. Karmakar, ...'"""
    m = _COUNT_LABEL.match(entry)
    if m and re.search(r"paper|article|journal|conference|publication|total", m.group(0), re.IGNORECASE):
        return entry[m.end():].strip()
    return entry

def _is_non_citation_entry(entry):''')

# 2. extra non-citation rules
swap('    return len(e) <= 100 and e.endswith(":")',
'''    if re.match(r"\\s*(?:a\\s+)?total\\b", e, re.IGNORECASE) and len(e) <= 400 and not _CITATION_MARK.search(e):
        return True                                          # the author's own count line, e.g. "A total of 43 publications [...]"
    if len(e) <= 60 and not re.search(r"\\d|,", e) and _BARE_LABEL.fullmatch(e):
        return True                                          # bare sub-heading such as "Journal Articles"
    return len(e) <= 100 and e.endswith(":")''')

# 3. do not cut a reference right after an author initial such as ", M."
swap('        if len(before) < min_piece or text[pos - 1] not in ".)]0123456789" or not _REF_END.search(before[-80:]):',
     '        if len(before) < min_piece or text[pos - 1] not in ".)]0123456789" or not _REF_END.search(before[-80:]) or re.search(r",\\s*[A-Z]\\.$", before.rstrip()):')

# 4. strip count labels in the entry loop
swap("        for entry in [q for e in split_publication_entries(chunk) for q in split_glued_references(e)]:\n",
     "        for entry in [q for e in split_publication_entries(chunk) for q in split_glued_references(e)]:\n"
     "            entry = _strip_count_label(entry)\n"
     "            if not entry:\n"
     "                continue\n")

# 5. glued 'Chaptersin Books'
swap('r"\\bbook\\s+chapters?\\b|\\bchapters?\\s+in\\b"', 'r"\\bbook\\s+chapters?\\b|\\bchapters?\\s*in\\b"')

path.write_text(src, encoding="utf-8")
print("patched OK")
