"""Make the Streamlit UI run the REAL pipeline functions (pdfplumber Stage 1, segment_one_resume Stage 2, shared
Stage 3 builder) instead of its own copies, and make it launchable from any folder.
Asserts each anchor appears exactly once."""
from pathlib import Path

# ================= Stage 3: split process_resume into build_prediction + file writing =================
p3 = Path("src/extract_structured_information.py")
s3 = p3.read_text(encoding="utf-8")

head = ('def process_resume(section_file):\n'
        '    with open(section_file, "r", encoding="utf-8") as f: data = json.load(f)\n'
        '    file_name = data.get("file_name", section_file.name)\n'
        '    sections = data.get("sections", {})\n'
        '    prediction = get_empty_gt_schema()\n')
tail = '    norm_name = section_file.name.replace("_sections.json", ".json")\n'
assert s3.count(head) == 1, "process_resume head count %d" % s3.count(head)
assert s3.count(tail) == 1, "process_resume tail count %d" % s3.count(tail)
i0 = s3.index(head); i1 = s3.index(tail)
body = s3[i0 + len(head):i1]
new_block = ('def build_prediction(data):\n'
             '    """Full Stage 3 for one resume: data = {"sections": {...}, "publication_groups": [...]}."""\n'
             '    sections = data.get("sections", {})\n'
             '    prediction = get_empty_gt_schema()\n'
             + body.rstrip() + '\n    return prediction\n\n\n'
             'def process_resume(section_file):\n'
             '    with open(section_file, "r", encoding="utf-8") as f: data = json.load(f)\n'
             '    prediction = build_prediction(data)\n\n')
s3 = s3[:i0] + new_block + s3[i1:]
p3.write_text(s3, encoding="utf-8")

# ================= UI =================
pu = Path("src/explainability/streamlit_app.py")
su = pu.read_text(encoding="utf-8")

def swap(old, new):
    global su
    assert su.count(old) == 1, "UI anchor count %d for: %s" % (su.count(old), old[:70])
    su = su.replace(old, new)

swap('import pypdf\nimport streamlit as st\n', 'import sys\nimport tempfile\n\nimport streamlit as st\n')
swap('PROJECT_ROOT = Path(r"c:\\Users\\Shrey\\Desktop\\TUF_F15_Data\\Shrey_academics\\MINOR\\Attempt_2\\synthetic-supervised-parser")\n',
     'PROJECT_ROOT = Path(__file__).resolve().parents[2]\nif str(PROJECT_ROOT) not in sys.path:\n    sys.path.insert(0, str(PROJECT_ROOT))\n')
swap('from src.extract_structured_information import (\n',
     'from src.extract_text_audited import extract_pdf_with_pdfplumber\n'
     'from src.segment_resumes_into_sections import segment_one_resume\n'
     'from src.extract_structured_information import (\n    build_prediction,\n')

old_s1_start = 'def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, int]:\n'
old_s1_end = '    return text, len(text)\n'
assert su.count(old_s1_start) == 1 and su.count(old_s1_end) == 1
a = su.index(old_s1_start); b = su.index(old_s1_end) + len(old_s1_end)
su = su[:a] + ('def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, int]:\n'
               '    """Stage 1 exactly as the pipeline runs it (pdfplumber, glued-word retry, page markers)."""\n'
               '    with tempfile.TemporaryDirectory() as tmp:\n'
               '        pdf_path = Path(tmp) / "upload.pdf"\n'
               '        pdf_path.write_bytes(pdf_bytes)\n'
               '        text = extract_pdf_with_pdfplumber(pdf_path)["full_text"].strip()\n'
               '    return text, len(text)\n') + su[b:]

swap('    sections = live_section_text(raw_text) if raw_text else {}\n',
     '    sections, publication_groups = {}, []\n'
     '    if raw_text:\n'
     '        with tempfile.TemporaryDirectory() as tmp:\n'
     '            txt_path = Path(tmp) / (base_name + ".txt")\n'
     '            txt_path.write_text(raw_text, encoding="utf-8")\n'
     '            seg = segment_one_resume(txt_path, load_heading_lookup())\n'
     '        sections, publication_groups = seg["sections"], seg.get("publication_groups", [])\n')

b0 = '    prediction = get_empty_gt_schema()\n    prediction["personal_details"] = extract_personal_details(sections)\n'
b1 = '        prediction["publications"] = split_publications_by_type(pub_text)\n'
assert su.count(b0) == 1 and su.count(b1) == 1, "UI stage-3 anchors"
a = su.index(b0); b = su.index(b1) + len(b1)
su = su[:a] + '    prediction = build_prediction({"sections": sections, "publication_groups": publication_groups})\n' + su[b:]

pu.write_text(su, encoding="utf-8")
print("patched OK")
