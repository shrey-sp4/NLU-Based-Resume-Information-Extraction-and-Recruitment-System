p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "_typed_segments" in s:
    raise SystemExit("Already applied")

helpers = r'''# ---------- PUBLICATION TYPE FROM THE AUTHOR'S OWN HEADINGS ----------
# Evidence order: (1) the author's heading, (2) explicit per-entry marker, (3) text rules, (4) default journal.
_HEADING_TYPE_RULES = [
    ("preprints", r"\bin\s+progress\b|\bworking\s+papers?\b|\bunder\s+(?:review|submission)\b|\bsubmitted\b|\bpre-?prints?\b|\barxiv\b"),
    ("communications", r"\bcommunicated\b|\b(?:in|under)\s+communication\b"),
    ("book_chapters", r"\bbook\s+chapters?\b|\bchapters?\s+in\b"),
    ("technical_reports", r"\btechnical\s+reports?\b|\breports?\s+and\s+resource\b|\bwhite\s+papers?\b"),
    ("conference_proceedings", r"proceedings?"),
]
_HEAD_CONF = r"conference|symposi|\bworkshops?\b|\bseminars?\b|\bpresentations?\b"
_HEAD_JOURNAL = r"journal(?!ism)|\bresearch\s+articles?\b|\bpapers\s+published\b|\bpublished\s*/\s*accepted\b|\btransactions\b"
_YEAR_HEADING = re.compile(r"^\s*(?:19|20)\d{2}\s+publications?\s*$", re.IGNORECASE)
_NON_PUB_LINE = re.compile(r"reviewer|taught|attended|organi[sz]ed|invited|lectures?|\btalks?\b|awarded|cover|highlight", re.IGNORECASE)
_COMMUNICATED_MARK = re.compile(r"\(\s*communicated\s*\)|\bcommunicated\.?\s*$", re.IGNORECASE)
# inline sub-headings are only trusted for the rare types; journal/conference context comes from Stage-2 headings
_INLINE_TYPES = {"preprints", "communications", "book_chapters", "technical_reports"}

def _heading_type(text):
    low = (text or "").lower()
    for bucket, pat in _HEADING_TYPE_RULES:
        if re.search(pat, low):
            return bucket
    has_conf = re.search(_HEAD_CONF, low)
    has_journal = re.search(_HEAD_JOURNAL, low)
    if has_conf and has_journal:
        return None                      # mixed heading such as "Journals / Conferences": no single type
    if has_conf:
        return "conference_papers"
    if has_journal:
        return "journal_articles"
    return None

def _inline_subheading(line):
    """('type', bucket) for a rare-type sub-heading line, ('reset', None) for a non-publication heading, else None."""
    if re.fullmatch(r"\(.*\)", line.strip()):
        return None                                          # "(Communicated)" is a suffix of the entry above, not a heading
    t = line.strip().strip(":-–—|•●■□*➢+ ").strip()
    t = re.sub(r"\s*[:\(]\s*\d+\s*\)?\s*$", "", t).strip()        # trailing count, e.g. "Book chapters: 3"
    if not t or len(t.split()) > 7 or len(t) > 60:
        return None
    if re.search(r"\d", t) or t.endswith((",", ".")):
        return None
    if _NON_PUB_LINE.search(t):
        return ("reset", None)
    bucket = _heading_type(t)
    if bucket in _INLINE_TYPES:
        return ("type", bucket)
    return None

def _typed_segments(text, groups):
    """List of (type_hint_or_None, chunk_text), using Stage-2 publication groups when available."""
    if not groups:
        groups = [{"heading": "", "text": text}]
    segments, prev_hint = [], None
    for g in groups:
        heading = g.get("heading", "")
        hint = _heading_type(heading)
        if hint is None and _YEAR_HEADING.match(heading):
            hint = prev_hint                                  # "2024 Publication" continues the section above
        prev_hint = hint
        ctx, buf = hint, []
        for line in (g.get("text") or "").splitlines():
            sub = _inline_subheading(line)
            if sub is not None:
                if buf:
                    segments.append((ctx, "\n".join(buf)))
                    buf = []
                ctx = sub[1] if sub[0] == "type" else hint
                continue                                     # a heading line is not a publication
            buf.append(line)
        if buf:
            segments.append((ctx, "\n".join(buf)))
    return segments

'''

old_fn = '''def split_publications_by_type(text):
    buckets = {
        "journal_articles": [], "conference_papers": [], "conference_proceedings": [],
        "communications": [], "book_chapters": [], "books": [],
        "technical_reports": [], "preprints": [],
    }
    for entry in [q for e in split_publication_entries(text) for q in split_glued_references(e)]:
        buckets[classify_publication(entry)].append(entry)
    return buckets
'''
new_fn = '''def split_publications_by_type(text, groups=None):
    buckets = {
        "journal_articles": [], "conference_papers": [], "conference_proceedings": [],
        "communications": [], "book_chapters": [], "books": [],
        "technical_reports": [], "preprints": [],
    }
    for hint, chunk in _typed_segments(text, groups):
        for entry in [q for e in split_publication_entries(chunk) for q in split_glued_references(e)]:
            if _COMMUNICATED_MARK.search(entry):
                bucket = "communications"                    # explicit "(Communicated)" marker on this entry
            else:
                bucket = hint or classify_publication(entry)
            buckets[bucket].append(entry)
    return buckets
'''
assert s.count(old_fn) == 1, "function anchor"
s = s.replace(old_fn, helpers + new_fn)

old_call = '        prediction["publications"] = split_publications_by_type(pub_text)\n'
new_call = '        prediction["publications"] = split_publications_by_type(pub_text, data.get("publication_groups"))\n'
assert s.count(old_call) == 1, "call anchor"
s = s.replace(old_call, new_call)
open(p, "w", encoding="utf-8").write(s)
print("applied")