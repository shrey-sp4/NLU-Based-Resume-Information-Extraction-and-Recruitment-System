from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from shortlisting.llm.client import ConfigurableLLMClient, LLMClient

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "publication_taxonomy.json"


class PublicationService:
    """
    Service to parse raw publication citations and classify tiers using a configurable LLM layer.
    Strictly ensures that raw citations, venues, and DOIs are never returned to candidate profile outputs.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, config_path: Optional[Path] = None):
        self.llm_client = llm_client or ConfigurableLLMClient()
        self.config_path = config_path or CONFIG_PATH
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.tier_definitions: Dict[str, str] = data.get("tier_definitions", {})
            self.default_fallback_tier: str = data.get("default_fallback_tier", "Unranked")
            prompt_template = data.get("system_prompt", "")
            formatted_tiers = "\n".join(f"- {k}: {v}" for k, v in self.tier_definitions.items())
            self.system_prompt = prompt_template.replace("{tier_definitions}", formatted_tiers)
        else:
            self.tier_definitions = {
                "Tier-1": "Top-tier peer-reviewed journals / CORE A* conferences",
                "Tier-2": "Recognized peer-reviewed journals / CORE B conferences",
                "Tier-3": "Regional conferences / local proceedings",
                "Unranked": "Preprints or unverified venues",
            }
            self.default_fallback_tier = "Unranked"
            self.system_prompt = "Parse citation and classify into Tier-1, Tier-2, Tier-3, or Unranked."

    def parse_and_classify_citation(
        self, raw_citation: str, category_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Parses raw citation text to extract title, type, year, and tier.
        Returns:
            {
                'title': str or None,
                'type': 'journal' | 'conference' | 'other',
                'year': str or None,
                'tier': str
            }
        Guarantees that raw citation, venue, and DOI are omitted.
        """
        if not raw_citation or not raw_citation.strip():
            return {
                "title": None,
                "type": "other",
                "year": None,
                "tier": self.default_fallback_tier,
            }

        user_prompt = f"Citation: {raw_citation.strip()}\nExtracted Category Hint: {category_hint.strip()}"
        try:
            res = self.llm_client.generate_json(self.system_prompt, user_prompt)
            tier = res.get("tier", self.default_fallback_tier)
            if tier not in self.tier_definitions:
                tier = self.default_fallback_tier

            # If fallback was used or evidence was insufficient, tier must be Unranked
            if res.get("_is_fallback", False):
                tier = "Unranked"

            pub_type = str(res.get("type", "other")).lower().strip()
            if pub_type not in ("journal", "conference", "other"):
                pub_type = "other"

            year = res.get("year")
            if year is not None:
                year_str = str(year).strip()
                # Validate year format (4 digits)
                import re

                if not re.fullmatch(r"(?:19|20)\d{2}", year_str):
                    year = None
                else:
                    year = year_str

            title = res.get("title")
            title_str = str(title).strip() if title else ""

            return {
                "title": title_str or None,
                "type": pub_type,
                "year": year,
                "tier": tier,
            }
        except Exception:
            return {
                "title": None,
                "type": "other",
                "year": None,
                "tier": self.default_fallback_tier,
            }
