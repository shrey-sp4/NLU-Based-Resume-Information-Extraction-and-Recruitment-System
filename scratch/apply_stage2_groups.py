p = "src/segment_resumes_into_sections.py"
s = open(p, encoding="utf-8").read()
if "publication_groups" in s:
    raise SystemExit("Already applied")

def swap(old, new, tag):
    global s
    assert s.count(old) == 1, "anchor not found exactly once: " + tag
    s = s.replace(old, new)

swap("    current_section = \"preamble\"\n\n    for line_number, line in enumerate(lines, start=1):",
     "    current_section = \"preamble\"\n    publication_groups: List[Dict[str, Any]] = []   # heading + its lines, for every publications heading\n\n    for line_number, line in enumerate(lines, start=1):",
     "init")

swap("                elif not NOISE_LINE.search(raw_line):\n                    append_line(sections, current_section, raw_line)   # false heading: keep as normal text\n",
     "                elif not NOISE_LINE.search(raw_line):\n                    append_line(sections, current_section, raw_line)   # false heading: keep as normal text\n                    if current_section == \"publications\" and publication_groups:\n                        publication_groups[-1][\"lines\"].append(raw_line)\n",
     "false heading")

swap("            remaining = heading_info.get(\"remaining_text\", \"\").strip()\n            if remaining:\n                append_line(sections, current_section, remaining)\n        else:\n            append_line(sections, current_section, raw_line)\n",
     "            if canonical == \"publications\":\n                publication_groups.append({\"heading\": heading_info[\"clean_heading\"], \"lines\": []})\n\n            remaining = heading_info.get(\"remaining_text\", \"\").strip()\n            if remaining:\n                append_line(sections, current_section, remaining)\n                if canonical == \"publications\":\n                    publication_groups[-1][\"lines\"].append(remaining)\n        else:\n            append_line(sections, current_section, raw_line)\n            if current_section == \"publications\" and publication_groups:\n                publication_groups[-1][\"lines\"].append(raw_line)\n",
     "body lines")

swap("        \"boundaries\": boundaries,\n        \"ignored_headings\": ignored_headings,\n    }\n",
     "        \"boundaries\": boundaries,\n        \"ignored_headings\": ignored_headings,\n        \"publication_groups\": [\n            {\"heading\": g[\"heading\"], \"text\": \"\\n\".join(g[\"lines\"]).strip()}\n            for g in publication_groups if \"\\n\".join(g[\"lines\"]).strip()\n        ],\n    }\n",
     "return")
open(p, "w", encoding="utf-8").write(s)
print("applied")