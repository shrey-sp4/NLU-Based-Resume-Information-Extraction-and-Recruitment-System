from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from shortlisting.models.candidate import NormalizedCandidate
from shortlisting.normalization.education_normalizer import EducationNormalizer
from shortlisting.normalization.experience_normalizer import ExperienceNormalizer
from shortlisting.normalization.publication_normalizer import PublicationNormalizer


import re

TITLE_PREFIX_REGEX = re.compile(
    r"^(?:(?:Dr|Prof|Mr|Mrs|Ms)\.?\s+)+",
    re.IGNORECASE,
)

CREDENTIALS_SUFFIX_REGEX = re.compile(
    r"(?:[,\s]+(?:SMIEEE|MIEEE|FIEEE|IEEE|Ph\.?D\.?|PhD|M\.?Tech\.?|B\.?Tech\.?|M\.?Sc\.?|B\.?Sc\.?|Post-?doc|Fellow))+\s*$",
    re.IGNORECASE,
)

REJECT_NAME_PATTERNS = [
    r"\bdepartment\b", r"\bschool\b", r"\bfaculty\b", r"\buniversity\b", r"\binstitute\b",
    r"\balgorithm\b", r"\bgrowth\b", r"\bindividual\b", r"\bcomprehension\b", r"\bdriving\b",
    r"\btechnical skills\b", r"\bcompetent\b", r"\bskills\b", r"\blanguages?\b",
    r"\bbengali\b", r"\bhindi\b", r"\benglish\b", r"\bgujarati\b",
    r"\bcurriculum\b", r"\bvitae\b", r"\bresume\b", r"\bbiodata\b",
    r"\bobjective\b", r"\bsummary\b", r"\bopportunities\b", r"\bseeking\b", r"\blooking for\b",
    r"\bdedicated\b", r"\bpossessing\b", r"\bcontribute\b", r"\bexperienced\b"
]
REJECT_NAME_REGEX = re.compile("|".join(REJECT_NAME_PATTERNS), re.IGNORECASE)


class CandidateNormalizer:
    """
    Coordinates ingestion from existing prediction JSONs (output/predictions/*.json)
    and strictly isolates only the approved candidate fields:
    candidate_name, education, experience, publications.
    """

    def __init__(
        self,
        edu_normalizer: Optional[EducationNormalizer] = None,
        exp_normalizer: Optional[ExperienceNormalizer] = None,
        pub_normalizer: Optional[PublicationNormalizer] = None,
    ):
        self.edu_normalizer = edu_normalizer or EducationNormalizer()
        self.exp_normalizer = exp_normalizer or ExperienceNormalizer()
        self.pub_normalizer = pub_normalizer or PublicationNormalizer()

    @staticmethod
    def clean_candidate_name(raw_name: str) -> str:
        """
        Cleans candidate name by removing attached title prefixes (Dr., Prof.)
        and credentials/affiliations (SMIEEE, Ph.D., etc.), while strictly
        rejecting non-person text (departments, skills, headers, languages).
        Returns empty string if name is invalid or unidentifiable.
        """
        if not raw_name:
            return ""
        name = raw_name.strip()

        # 1. Strip credential suffixes (e.g. SMIEEE, Ph.D., M.Tech)
        name = CREDENTIALS_SUFFIX_REGEX.sub("", name).strip()
        # 2. Strip title prefixes (e.g. Dr., Prof., Mr., Ms., Mrs.)
        name = TITLE_PREFIX_REGEX.sub("", name).strip()
        name = name.strip(" ,;:-–—.")

        # 3. Reject non-person text patterns
        if REJECT_NAME_REGEX.search(name):
            return ""

        words = name.split()
        if len(words) < 2 or len(words) > 5:
            return ""

        # Reject if contains English prepositions/conjunctions indicating sentences
        if any(w.lower() in ("and", "to", "for", "with", "of", "in", "the", "on", "at") for w in words):
            return ""

        return name

    def normalize_dict(self, raw_pred: Dict[str, Any]) -> NormalizedCandidate:
        """Normalizes a loaded prediction dictionary."""
        # 1. Candidate Name (strictly from personal_details.name with validation)
        personal_details = raw_pred.get("personal_details", {})
        raw_candidate_name = ""
        if isinstance(personal_details, dict):
            raw_candidate_name = str(personal_details.get("name", "") or "").strip()
        candidate_name = self.clean_candidate_name(raw_candidate_name)

        # 2. Education
        raw_education = raw_pred.get("education", [])
        education_entries = self.edu_normalizer.normalize(raw_education)

        # 3. Experience
        raw_experience = raw_pred.get("experience", [])
        experience_entries = self.exp_normalizer.normalize(raw_experience)

        # 4. Publications
        raw_publications = raw_pred.get("publications", {})
        publication_entries = self.pub_normalizer.normalize(raw_publications)

        return NormalizedCandidate(
            candidate_name=candidate_name,
            education=education_entries,
            experience=experience_entries,
            publications=publication_entries,
        )

    def normalize_file(self, file_path: Path | str) -> NormalizedCandidate:
        """Reads prediction JSON from disk and returns normalized candidate model."""
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.normalize_dict(data)
