p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "_is_activity_entry" in s:
    raise SystemExit("Already applied")

def swap(old, new, tag):
    global s
    assert s.count(old) == 1, "anchor not found exactly once: " + tag
    s = s.replace(old, new)

swap('awarded|cover|highlight", re.IGNORECASE)', 'awarded|\\bcover\\b|highlight", re.IGNORECASE)', "cover word boundary")

swap('_COMMUNICATED_MARK = re.compile(r"\\(\\s*communicated\\s*\\)|\\bcommunicated\\.?\\s*$", re.IGNORECASE)\n',
'''_COMMUNICATED_MARK = re.compile(r"\\(\\s*communicated\\s*\\)|\\bcommunicated\\.?\\s*$", re.IGNORECASE)
# activity lines (workshops attended, talks given, sessions chaired) are not publications
_ACTIVITY_ENTRY = re.compile(
    r"^\\s*(?:[\\[\\(]?\\d{1,3}[\\.\\)\\]]\\s*)?(?:participated|attended|delivered|co-?chaired|chaired|organi[sz]ed|conducted|"
    r"co-?ordinated|moderated|served|acted|completed|undergone|invited\\s+(?:talk|lecture)|expert\\s+talk|resource\\s+person|guest\\s+lecture)\\b",
    re.IGNORECASE)
_CITATION_MARK = re.compile(r"\\bpp?\\.?\\s*\\d|\\bvol\\.?\\s*\\d|\\bdoi\\b|\\bissn\\b|\\d+\\s*\\(\\d+\\)\\s*,?\\s*\\d+\\s*[-–]\\s*\\d+", re.IGNORECASE)

def _is_activity_entry(entry):
    return bool(_ACTIVITY_ENTRY.match(entry)) and not _CITATION_MARK.search(entry)
''', "activity definitions")

swap('''        for entry in [q for e in split_publication_entries(chunk) for q in split_glued_references(e)]:
            if _COMMUNICATED_MARK.search(entry):''',
'''        for entry in [q for e in split_publication_entries(chunk) for q in split_glued_references(e)]:
            if _is_activity_entry(entry):
                continue                                     # talks, workshops attended, sessions chaired: not publications
            if _COMMUNICATED_MARK.search(entry):''', "loop")
open(p, "w", encoding="utf-8").write(s)
print("applied")