import re

JOB_TITLE_WORDS = re.compile(
    r"\b(?:Professor|Scientist|Scholar|Engineer|Manager|Director|Postdoctoral|Lecturer|Researcher|Fellow|Experienced|Graduate|Student|Assistant|Associate|Executive|Consultant|Developer|Analyst|Lead|Head|Officer|Member)\b",
    re.IGNORECASE
)

ADDRESS_WORDS = re.compile(
    r"\b(?:Road|Street|Avenue|Boulevard|Lane|Drive|Kolkata|Hyderabad|Delhi|Mumbai|Chennai|Bangalore|Gujarat|India|Campus|Building|Floor|Suite|Block|Sector|Apartment|Society|Pincode|School)\b",
    re.IGNORECASE
)

PREAMBLE_HEADER_NOISE = re.compile(
    r"\b(?:curricu?lam|curriculum|vitae|resume|biodata|profile|page\s+\d+|page|recognized|top\s+\d+%|stanford|elsevier|webpage|google scholar|looking for|achievements|opportunities|qualified|gold medalist)\b",
    re.IGNORECASE
)

def test_extract_name(raw_lines):
    if len(raw_lines) >= 2:
        l1, l2 = raw_lines[0], raw_lines[1]
        if (len(l1.split()) == 1 and len(l2.split()) == 1 and 
            re.match(r"^[A-Z][a-z]+$", l1) and re.match(r"^[A-Z][a-z]+$", l2)):
            return f"{l1} {l2}"

    for raw_l in raw_lines[:12]:
        if "@" in raw_l or "http" in raw_l or "www." in raw_l:
            continue
        if PREAMBLE_HEADER_NOISE.search(raw_l):
            continue
        
        sub_lines = re.split(r"\s{3,}", raw_l)
        for line in sub_lines:
            line = line.strip()
            if not line or "@" in line or "http" in line:
                continue
            if PREAMBLE_HEADER_NOISE.search(line):
                continue
            if JOB_TITLE_WORDS.search(line):
                continue
            if ADDRESS_WORDS.search(line):
                continue

            clean_line = re.sub(r"^(?:name|full name|candidate name)\s*[:\-]\s*", "", line, flags=re.IGNORECASE).strip()
            clean_line = clean_line.strip(":-–—|•●■□*➢+ ")
            clean_line = re.split(r"\b(?:Address|Email|E-mail|Phone|Mobile|Contact|Location|Webpage|CV page|Page)\b", clean_line, flags=re.IGNORECASE)[0].strip()
            clean_line = re.split(r"\d", clean_line)[0].strip()
            clean_line = re.sub(r"[^\w\s\.\-']", "", clean_line).strip()

            words = clean_line.split()
            if 2 <= len(words) <= 5 and re.match(r"^[A-Za-z\.\s\-']+$", clean_line):
                return clean_line
    return ""

print("Doyel   :", test_extract_name(["Doyel", "Mukherjee", "doyel.mukherjee90@gmail.com"]))
print("Dibakar :", test_extract_name(["Dibakar Roy Chowdhury           Ecole Centrale School of Engineering,"]))
print("Dhwanil :", test_extract_name(["DHWANILNATH GAUTAM", "(formerly Dhwanilnath Gharekhan)"]))
print("Priyanka:", test_extract_name(["Dr. Priyanka Sharma", "Address: Ludhiana, Punjab-141014"]))
