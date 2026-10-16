p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "_is_non_citation_entry" in s:
    raise SystemExit("Already applied")

def swap(old, new, tag):
    global s
    assert s.count(old) == 1, "anchor not found exactly once: " + tag
    s = s.replace(old, new)

# 1. keynote / plenary / panel are talks, not papers
swap("completed|undergone|", "completed|undergone|keynote|plenary|panel(?:ist)?|", "activity verbs")

# 2. entries that are not citations: glyph junk, citation-metrics lines, short label lines ending in ':'
swap('''def _is_activity_entry(entry):
    return bool(_ACTIVITY_ENTRY.match(entry)) and not _CITATION_MARK.search(entry)
''', '''def _is_activity_entry(entry):
    return bool(_ACTIVITY_ENTRY.match(entry)) and not _CITATION_MARK.search(entry)

_METRICS_LINE = re.compile(r"\\bh-?\\s?index\\b|\\bi-?10\\s?-?index\\b|citations?\\s+per\\s+paper|total\\s+citations?|total\\s+publications?", re.IGNORECASE)

def _is_non_citation_entry(entry):
    """PDF glyph junk, citation-metric lines and short label lines such as 'International(abroad):' are not publications."""
    e = entry.strip()
    if re.fullmatch(r"(?:\\(cid:\\d+\\)\\s*)+", e):
        return True
    if len(e) <= 250 and _METRICS_LINE.search(e[:40]) and not _CITATION_MARK.search(e):
        return True
    return len(e) <= 100 and e.endswith(":")
''', "non-citation helper")

# 3. headings that start a non-publication LIST (reviewer lists, courses taught) skip until the next heading
swap('_NON_PUB_LINE = re.compile(', '_SKIP = "__skip__"\n_SKIP_BLOCK_LINE = re.compile(r"reviewer|reviewing|referee|\\btaught\\b|courses?\\s+(?:taught|handled)", re.IGNORECASE)\n_NON_PUB_LINE = re.compile(', "skip constants")

swap('''    if _NON_PUB_LINE.search(t):
        return ("reset", None)''', '''    if _SKIP_BLOCK_LINE.search(t):
        return ("skip", None)                                # the list under this heading is not publications
    if _NON_PUB_LINE.search(t):
        return ("reset", None)''', "skip return")

swap('''                if buf:
                    segments.append((ctx, "\\n".join(buf)))
                    buf = []
                ctx = sub[1] if sub[0] == "type" else hint
                continue''', '''                if buf and ctx != _SKIP:
                    segments.append((ctx, "\\n".join(buf)))
                buf = []
                ctx = sub[1] if sub[0] == "type" else (_SKIP if sub[0] == "skip" else hint)
                continue''', "typed segments switch")

swap('''        if buf:
            segments.append((ctx, "\\n".join(buf)))
    return segments''', '''        if buf and ctx != _SKIP:
            segments.append((ctx, "\\n".join(buf)))
    return segments''', "typed segments end")

swap('''            if _is_activity_entry(entry):
                continue                                     # talks, workshops attended, sessions chaired: not publications''',
'''            if _is_activity_entry(entry) or _is_non_citation_entry(entry):
                continue                                     # talks, workshops attended, labels, metrics, glyph junk: not publications''', "loop")
open(p, "w", encoding="utf-8").write(s)
print("applied")