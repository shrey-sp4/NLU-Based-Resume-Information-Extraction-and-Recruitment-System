"""Widen the email-context name fallback: scan every line (sections are joined in arbitrary order, so 'near the email'
is meaningless). Safe because a candidate must still share at least two words with the email address.
Asserts each anchor appears exactly once."""
from pathlib import Path

path = Path("src/extract_structured_information.py")
src = path.read_text(encoding="utf-8")

old = ('    lines = [l.strip() for l in text.splitlines()]\n'
       '    hits = [i for i, l in enumerate(lines) if email in l]\n'
       '    if not hits:\n'
       '        return ""\n'
       '    for l in lines[max(0, hits[0] - 12): hits[0] + 13]:\n')
new = ('    lines = [l.strip() for l in text.splitlines()]\n'
       '    for l in lines:\n')
assert src.count(old) == 1, "anchor count %d" % src.count(old)
src = src.replace(old, new)
old_doc = '"""Name-shaped line near the email whose words (at least two) appear in the email address; else empty."""'
assert src.count(old_doc) == 1
src = src.replace(old_doc, '"""Name-shaped line anywhere in the text whose words (at least two) appear in the email address; else empty."""')
path.write_text(src, encoding="utf-8")
print("patched OK")
