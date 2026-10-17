p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "_STATUS_SUFFIX" in s:
    raise SystemExit("Already applied")

def swap(old, new, tag):
    global s
    assert s.count(old) == 1, "anchor not found exactly once: " + tag
    s = s.replace(old, new)

swap('_SKIP = "__skip__"\n',
     '_SKIP = "__skip__"\n_STATUS_SUFFIX = re.compile(r"\\(\\s*(?:communicated|accepted|submitted|published|in\\s+press|under\\s+review|to\\s+appear)\\s*\\)\\s*\\.?\\s*$", re.IGNORECASE)\n',
     "status suffix constant")

swap('''    if re.fullmatch(r"\\(.*\\)", line.strip()):
        return None                                          # "(Communicated)" is a suffix of the entry above, not a heading''',
'''    if re.fullmatch(r"\\(.*\\)", line.strip()) or _STATUS_SUFFIX.search(line.strip()):
        return None                                          # "(Communicated)" or "... title. (Communicated)" ends an entry; it is not a heading''',
     "inline subheading guard")
open(p, "w", encoding="utf-8").write(s)
print("applied")