p = "src/extract_structured_information.py"
s = open(p, encoding="utf-8").read()
if "_pick_name" in s:
    raise SystemExit("Name patch already applied - run: git checkout src/extract_structured_information.py first")

helpers = '''_NAME_PARTICLES = {"de", "van", "von", "bin", "al", "da", "di", "la", "le", "ibn", "del", "der"}
_NAME_TITLES = {"dr", "prof", "mr", "mrs", "ms", "shri", "smt", "er"}
_NAME_SUFFIXES = {"ph.d.", "ph.d", "phd", "smieee", "mieee", "ieee"}
_FUNCTION_WORDS = {"a", "an", "the", "of", "and", "or", "for", "in", "on", "at", "to", "by", "with",
                   "is", "are", "as", "who", "that", "from", "into", "over", "under"}

def _name_shape_ok(name):
    """True if the text is shaped like a person's name: 2-5 words, capitalised words, initials,
    titles, particles or a short lowercase surname - never function words or long lowercase words."""
    toks = [t for t in name.split() if t]
    if not 2 <= len(toks) <= 5:
        return False
    core = 0
    for t in toks:
        base = t.strip(",")
        low = base.lower().rstrip(".")
        if base.lower() in _NAME_SUFFIXES or low in _NAME_TITLES:
            continue
        if low in _NAME_PARTICLES:
            continue
        if re.match(r"^[A-Z][A-Za-z'\\-]*\\.?$", base) or re.match(r"^(?:[A-Z]\\.)+$", base):
            core += 1
            continue
        if base.isalpha() and base.islower() and len(base) <= 6 and low not in _FUNCTION_WORDS:
            core += 1
            continue
        return False
    return core >= 2

def _pick_name(candidates, email):
    """Prefer a name-shaped candidate whose words appear in the email address; else the first name-shaped one."""
    local = re.sub(r"[^a-z]", "", email.split("@")[0].lower()) if email else ""
    shaped = [c for c in candidates if _name_shape_ok(c)]
    for c in shaped:
        words = [w for w in re.findall(r"[a-z]+", c.lower()) if len(w) >= 3 and w not in _NAME_TITLES and w not in _NAME_SUFFIXES]
        if local and any(w in local for w in words):
            return c
    return shaped[0] if shaped else ""

'''
a = "def extract_personal_details(sections):"
assert s.count(a) == 1, "anchor 1"
s = s.replace(a, helpers + a)

old1 = "    if not name:\n        for raw_l in raw_lines[:12]:"
new1 = "    if not name:\n        name_candidates = []\n        for raw_l in raw_lines[:12]:"
assert s.count(old1) == 1, "anchor 2"
s = s.replace(old1, new1)

old2 = ("                if 2 <= len(words) <= 5 and re.match(r\"^[A-Za-z\\.\\s\\-']+$\", clean_line):\n"
        "                    name = clean_line\n"
        "                    break\n"
        "            if name:\n"
        "                break\n")
new2 = ("                if 2 <= len(words) <= 5 and re.match(r\"^[A-Za-z\\.\\s\\-']+$\", clean_line):\n"
        "                    name_candidates.append(clean_line)\n"
        "        name = _pick_name(name_candidates, email)\n")
assert s.count(old2) == 1, "anchor 3"
s = s.replace(old2, new2)
open(p, "w", encoding="utf-8").write(s)
print("Name patch applied")