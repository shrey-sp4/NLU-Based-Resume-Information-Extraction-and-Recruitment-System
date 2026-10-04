from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from shortlisting.llm.client import ConfigurableLLMClient, LLMClient

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "university_taxonomy.json"


import re

TABLE_HEADER_REGEX = re.compile(
    r"\b(?:degree\s+university|board/university|university/board|college/school|"
    r"percentage\s+passing|year\s+of\s+percentage|division\s+completion|"
    r"year\s+of\s+passing|in\s+which\s+year|level\s+board|passing\s+year)\b",
    re.IGNORECASE,
)

SECONDARY_BOARD_REGEX = re.compile(
    r"\b(?:council\s+of\s+higher\s+secondary|council\s+of\s+secondary|board\s+of\s+secondary|"
    r"secondary\s+education|school\s+examination|cbse|icse|wbbse|wbchse|up\s+board|jk\s+board|"
    r"bsemp|gsheb|madhyamik|matric|secondary\s+school)\b",
    re.IGNORECASE,
)

NON_INSTITUTION_REGEX = re.compile(
    r"\b(?:diagnostic\s+strategies|induction\s+motor|thermal\s+imaging|"
    r"forest\s+management|himalayan\s+region|social\s+sciences|cgpa|percentage)\b",
    re.IGNORECASE,
)

VALID_INSTITUTION_TOKENS = re.compile(
    r"\b(?:university|institute|college|school\s+of|academy|vishwavidyalaya|vidyapeeth|"
    r"iit|nit|iiit|iim|iiser|iisc|bhu|jnu|bits|daiict)\b",
    re.IGNORECASE,
)


class UniversityTierService:
    """Service to categorize educational institutions into tiers using a configurable LLM layer."""

    def __init__(self, llm_client: Optional[LLMClient] = None, config_path: Optional[Path] = None):
        self.llm_client = llm_client or ConfigurableLLMClient()
        self.config_path = config_path or CONFIG_PATH
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.tier_definitions: Dict[str, str] = data.get("tier_definitions", {})
            self.default_fallback_tier: str = data.get("default_fallback_tier", "Unknown")
            prompt_template = data.get("system_prompt", "")
            formatted_tiers = "\n".join(f"- {k}: {v}" for k, v in self.tier_definitions.items())
            self.system_prompt = prompt_template.replace("{tier_definitions}", formatted_tiers)
        else:
            self.tier_definitions = {
                "Tier-1": "Premier research university",
                "Tier-2": "Accredited state/autonomous university",
                "Tier-3": "Regional affiliated college",
                "Unknown": "Unrecognized or missing institution",
            }
            self.default_fallback_tier = "Unknown"
            self.system_prompt = "Classify institution into Tier-1, Tier-2, Tier-3, or Unknown."

    def categorize_institution(self, institution: str, degree: str = "") -> Dict[str, Any]:
        """
        Categorizes an educational institution into a configured tier.
        Returns: {'tier': str, 'confidence': float, 'reason': str}
        """
        inst_clean = (institution or "").strip()
        if not inst_clean:
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": "Institution name is empty or missing.",
            }

        # Guard against table column headers
        if TABLE_HEADER_REGEX.search(inst_clean):
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": "Input is a table column header, not an educational institution.",
            }

        # Guard against school examination boards
        if SECONDARY_BOARD_REGEX.search(inst_clean):
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": "Input is a secondary school examination board, not a higher-ed institution.",
            }

        # Guard against thesis topics / coursework / metrics
        if NON_INSTITUTION_REGEX.search(inst_clean):
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": "Input is a topic or non-institutional phrase.",
            }

        # Check for presence of legitimate institutional evidence
        if not VALID_INSTITUTION_TOKENS.search(inst_clean) and len(inst_clean.split()) < 2:
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": "Insufficient institutional evidence to classify tier.",
            }

        user_prompt = f"Institution: {inst_clean}\nDegree: {degree.strip()}"
        try:
            res = self.llm_client.generate_json(self.system_prompt, user_prompt)
            tier = res.get("tier", self.default_fallback_tier)
            if tier not in self.tier_definitions:
                tier = self.default_fallback_tier
            return {
                "tier": tier,
                "confidence": float(res.get("confidence", 0.5)),
                "reason": str(res.get("reason", "")),
            }
        except Exception as exc:
            return {
                "tier": self.default_fallback_tier,
                "confidence": 0.0,
                "reason": f"Categorization fallback due to: {exc}",
            }
