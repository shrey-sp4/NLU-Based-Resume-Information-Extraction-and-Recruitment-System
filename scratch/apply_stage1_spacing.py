"""Stage 1: re-extract a page with a tighter x_tolerance only when the page has glued (no-space) words.
Clean pages are untouched. Asserts each anchor appears exactly once."""
from pathlib import Path

path = Path("src/extract_text_audited.py")
src = path.read_text(encoding="utf-8")

anchor_def = "def extract_pdf_with_pdfplumber(pdf_path: Path) -> Dict[str, Any]:"
anchor_call = '            raw_text = page.extract_text() or ""'
assert src.count(anchor_def) == 1, "def anchor count: %d" % src.count(anchor_def)
assert src.count(anchor_call) == 1, "call anchor count: %d" % src.count(anchor_call)

helper = '''GLUED_WORD_REGEX = re.compile(r"[A-Za-z]{22,}")
TIGHT_X_TOLERANCE = 1.5


def extract_page_text(page) -> str:
    """Default extraction; if the page shows glued words (missing spaces), retry
    with a tighter x_tolerance and keep the retry only if it has fewer glued words."""
    text = page.extract_text() or ""
    glued_before = len(GLUED_WORD_REGEX.findall(text))
    if glued_before == 0:
        return text
    retry = page.extract_text(x_tolerance=TIGHT_X_TOLERANCE) or ""
    if len(GLUED_WORD_REGEX.findall(retry)) < glued_before:
        return retry
    return text


'''
src = src.replace(anchor_def, helper + anchor_def)
src = src.replace(anchor_call, "            raw_text = extract_page_text(page)")
path.write_text(src, encoding="utf-8")
print("patched OK")