from pathlib import Path

path = Path("src/segment_resumes_into_sections.py")
src = path.read_text(encoding="utf-8")

a_def = "def segment_one_resume(txt_path: Path, heading_lookup: Dict[str, str]) -> Dict[str, Any]:"
a_pre = '    current_section = "preamble"\n'
a_cur = "            current_section = canonical\n"
for name, a in (("def", a_def), ("preamble", a_pre), ("current", a_cur)):
    assert src.count(a) == 1, "%s anchor count: %d" % (name, src.count(a))

helper = '''# Sub-headings inside a publications list that must not end the publications section.
PUB_SUBHEADING_REGEX = re.compile(
    r"journal|conference|proceeding|paper|publication|article|book|chapter|report|preprint|"
    r"communicat|working|review|presented|international|national", re.IGNORECASE)


'''
src = src.replace(a_def, helper + a_def)

src = src.replace(a_pre, a_pre + '''    line_counts: Dict[str, int] = {}
    for _l in lines:
        _k = clean_line(_l).lower()
        line_counts[_k] = line_counts.get(_k, 0) + 1
''')

block = '''            if canonical == "other_sections":
                heading_key = clean_line(raw_line).lower()
                if len(heading_key) <= 60 and line_counts.get(heading_key, 0) >= 3:
                    continue                            # running page header: noise, not a section
                if current_section == "publications" and PUB_SUBHEADING_REGEX.search(heading_info["clean_heading"]):
                    if not NOISE_LINE.search(raw_line):
                        append_line(sections, current_section, raw_line)   # sub-heading inside the list: keep as text
                        if publication_groups:
                            publication_groups[-1]["lines"].append(raw_line)
                    continue

'''
src = src.replace(a_cur, block + a_cur)
path.write_text(src, encoding="utf-8")
print("patched OK")
