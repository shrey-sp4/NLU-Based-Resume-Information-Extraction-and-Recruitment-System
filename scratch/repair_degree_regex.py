import subprocess

p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "DEGREE_LINE_START_REGEX = re.compile(" in s:
    print("DEGREE_LINE_START_REGEX already present - nothing to repair")
    raise SystemExit
orig = subprocess.run(["git", "show", "HEAD:" + p], capture_output=True, encoding="utf-8", check=True).stdout
start = orig.index("DEGREE_LINE_START_REGEX = re.compile(")
end = orig.index("def split_section_into_entries")
block = orig[start:end]
anchor = "def split_section_into_entries"
assert s.count(anchor) == 1, "split_section_into_entries not found exactly once"
s = s.replace(anchor, block + anchor)
open(p, "w", encoding="utf-8").write(s)
print("Restored DEGREE_LINE_START_REGEX (%d lines)" % block.count("\n"))