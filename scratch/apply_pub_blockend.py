"""Stage 3: a heading-derived type block (e.g. book chapters, proceedings) must end when a later journal/conference/proceedings
heading appears. Asserts each anchor appears exactly once."""
from pathlib import Path

path = Path("src/extract_structured_information.py")
src = path.read_text(encoding="utf-8")

def swap(old, new):
    global src
    assert src.count(old) == 1, "anchor count %d for: %s" % (src.count(old), old[:60])
    src = src.replace(old, new)

swap("def _typed_segments(text, groups):", '''def _plain_heading_bucket(line):
    """Bucket named by a short heading-like line (any type), or None if the line is not heading-shaped."""
    t = line.strip().strip(":-\\u2013\\u2014|\\u2022\\u25cf\\u25a0\\u25a1*\\u27a2+ ").strip()
    t = re.sub(r"\\s*[:\\(]\\s*\\d+\\s*\\)?\\s*$", "", t).strip()
    if not t or len(t.split()) > 8 or len(t) > 70 or re.search(r"\\d", t) or t.endswith((",", ".")):
        return None
    return _heading_type(t)

def _typed_segments(text, groups):''')

swap("            sub = _inline_subheading(line)\n            if sub is not None:\n",
     "            sub = _inline_subheading(line)\n"
     "            if sub is None and ctx is not None and ctx != hint and ctx != _SKIP:\n"
     "                other = _plain_heading_bucket(line)\n"
     "                if other is not None and other != ctx:\n"
     "                    sub = (\"type\", other)                 # leaving a rare-type block via an explicit journal/conference heading\n"
     "            if sub is not None:\n")

path.write_text(src, encoding="utf-8")
print("patched OK")
