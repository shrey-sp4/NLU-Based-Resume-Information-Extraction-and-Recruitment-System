from __future__ import annotations

from typing import Dict, Set

# Academic Degree Gazetteers
DEGREE_GAZETTEER: Set[str] = {
    "b.tech", "m.tech", "ph.d.", "phd", "b.e.", "m.e.", "b.sc", "m.sc", "b.c.a.", "m.c.a.",
    "b.b.a.", "m.b.a.", "diploma", "hsc", "ssc", "matriculation", "intermediate", "higher secondary",
    "bachelor of technology", "master of technology", "doctor of philosophy", "bachelor of science",
    "master of science", "bachelor of engineering", "master of engineering", "bachelor of computer applications",
    "master of computer applications", "bachelor of business administration", "master of business administration"
}

# Technical Skill Gazetteers
SKILL_GAZETTEER: Set[str] = {
    "python", "java", "c++", "c#", "c", "r", "matlab", "javascript", "typescript", "html", "css",
    "sql", "mysql", "postgresql", "mongodb", "oracle", "react", "angular", "vue", "node.js", "django",
    "flask", "fastapi", "spring", "spring boot", "docker", "kubernetes", "aws", "azure", "gcp",
    "git", "github", "linux", "unix", "bash", "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "tableau", "power bi", "hadoop", "spark", "kafka", "bootstrap", "tailwind",
    "sap", "autocad", "ansys", "solidworks", "embedded c", "microcontroller", "verilog", "vhdl"
}

# Language Gazetteers
LANGUAGE_GAZETTEER: Set[str] = {
    "english", "hindi", "bengali", "gujarati", "marathi", "tamil", "telugu", "kannada",
    "malayalam", "punjabi", "urdu", "french", "german", "spanish", "japanese", "chinese"
}

# Role Title Gazetteers
ROLE_TITLE_GAZETTEER: Set[str] = {
    "professor", "assistant professor", "associate professor", "research assistant",
    "teaching assistant", "postdoctoral fellow", "project fellow", "junior research fellow",
    "senior research fellow", "lecturer", "software engineer", "data scientist", "researcher",
    "developer", "analyst", "consultant", "head of department", "principal", "director"
}

# University Keywords
UNIVERSITY_KEYWORDS: Set[str] = {
    "university", "institute", "college", "school", "academy", "iit", "nit", "iiit", "bits", "iim"
}

# Award Keywords
AWARD_KEYWORDS: Set[str] = {
    "award", "scholarship", "fellowship", "gold medal", "best paper", "merit certificate",
    "first rank", "top performer", "ugc net", "gate", "wbset", "csir net"
}


def is_in_degree_gazetteer(text: str) -> bool:
    return text.lower().strip() in DEGREE_GAZETTEER


def is_in_skill_gazetteer(text: str) -> bool:
    return text.lower().strip() in SKILL_GAZETTEER


def is_in_language_gazetteer(text: str) -> bool:
    return text.lower().strip() in LANGUAGE_GAZETTEER


def is_in_role_title_gazetteer(text: str) -> bool:
    return text.lower().strip() in ROLE_TITLE_GAZETTEER
