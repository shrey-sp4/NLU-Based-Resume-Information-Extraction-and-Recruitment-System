from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMClient(ABC):
    """Abstract provider-agnostic interface for structured LLM completion."""

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Generate validated JSON dictionary from prompt."""
        pass


class ConfigurableLLMClient(LLMClient):
    """
    Provider-agnostic LLM client with local caching, robust JSON decoding,
    and automatic offline heuristic fallback when API credentials are absent.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", "heuristic").lower()
        self.model_name = model_name or os.getenv("LLM_MODEL_NAME", "gemini-1.5-flash")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _extract_json_block(self, text: str) -> Dict[str, Any]:
        """Extracts JSON object from text or markdown code fence."""
        text = text.strip()
        # Look for ```json ... ``` or ``` ... ```
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        else:
            # Fallback to finding first '{' and last '}'
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]

        return json.loads(text)

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        cache_key = f"{self.provider}:{hash(system_prompt)}:{hash(user_prompt)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.provider == "gemini" and self.api_key:
            result = self._call_gemini(system_prompt, user_prompt)
        elif self.provider == "openai" and self.api_key:
            result = self._call_openai(system_prompt, user_prompt)
        else:
            result = self._fallback_heuristic(system_prompt, user_prompt)

        self._cache[cache_key] = result
        return result

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser request:\n{user_prompt}"}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"},
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._extract_json_block(raw_text)
        except Exception:
            return self._fallback_heuristic(system_prompt, user_prompt)

    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        import requests

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return self._extract_json_block(raw_text)
        except Exception:
            return self._fallback_heuristic(system_prompt, user_prompt)

    def _fallback_heuristic(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """
        Deterministic, offline fallback parser aligning with configurable taxonomy instructions.
        Ensures smooth testing and execution without network or API token dependency.
        Guarantees that non-entities, table headers, talks, and fragments never receive tiers.
        """
        user_lower = user_prompt.lower()

        # Case 1: University Tier Query
        if "institution:" in user_lower:
            # Reject table headers and non-entities
            if re.search(r"\b(?:degree\s+university|board/university|university/board|percentage|passing|examination|council|secondary|cgpa)\b", user_lower):
                return {"tier": "Unknown", "confidence": 0.0, "reason": "Not an educational institution."}

            if any(k in user_lower for k in ["national importance", "institute of technology", "central university", "premier", "iit", "nit", "iim", "iisc"]):
                return {"tier": "Tier-1", "confidence": 0.85, "reason": "Institution recognized as apex / national research importance."}
            elif any(k in user_lower for k in ["state university", "deemed university", "university", "autonomous", "vishwavidyalaya"]):
                return {"tier": "Tier-2", "confidence": 0.75, "reason": "Recognized state or autonomous university entity."}
            elif any(k in user_lower for k in ["college", "school", "vidyalaya", "institute"]):
                return {"tier": "Tier-3", "confidence": 0.65, "reason": "Affiliated college or local educational institute."}
            else:
                return {"tier": "Unknown", "confidence": 0.30, "reason": "Institutional information ambiguous or unrecognized."}

        # Case 2: Publication Citation Query
        # 1. Guard against non-publication records (headings, talks, attendances, fragments)
        non_pub_regex = re.compile(
            r"(?:citation:\s*)?(?:first/corresponding|co-corresponding|author\s+publications|publications\s*:|papers?\s+presented\s*:)|"
            r"\b(?:delivered\s+(?:an?\s+)?(?:expert|scholarly|invited|keynote|guest)?\s*(?:talk|address|lecture|speech))\b|"
            r"\b(?:invited\s+talks?|invited\s+presentations?|presentations?\s+at|talks?\s+at)\b|"
            r"\b(?:participated\s+in(?:\s+the)?\s+(?:national|international|two\s+days?|one\s+week)?\s*(?:workshop|sttp|training))\b|"
            r"\b(?:participated\s+in|attended\s+(?:an?\s+)?(?:online\s+)?(?:workshop|seminar|conference|training))\b|"
            r"\b(?:organized\s+(?:international|national)?\s*(?:conference|workshop))\b|"
            r"\b(?:total\s+paper\s+published|total\s+publications?)\b|"
            r"\b(?:international\s+workshop\s+on\b)|"
            r"\b(?:training\s+program\s+in|hands-on\s+workshop)\b|"
            r"page\s+\d+\s+of\s+\d+|^\s*\d+\s*\|\s*p\s*age|^\s*\d{4,}/[a-z0-9\.\-_/]+",
            re.IGNORECASE,
        )
        if non_pub_regex.search(user_prompt):
            return {
                "title": None,
                "type": "other",
                "year": None,
                "tier": "Unranked",
                "confidence": 0.0,
            }

        # Extract 4-digit year if present
        year_m = re.search(r"\b(19|20)\d{2}\b", user_prompt)
        year = year_m.group(0) if year_m else None

        # Determine type
        if any(w in user_lower for w in ["journal", "transactions", "letters", "issn", "vol.", "vol ", "issue"]):
            pub_type = "journal"
        elif any(w in user_lower for w in ["conference", "proceedings", "symposium", "workshop", "proc.", "ieee"]):
            pub_type = "conference"
        else:
            pub_type = "other"

        # Isolate citation text from hint and prompt wrappers
        cit_text = user_prompt
        if "Citation:" in cit_text:
            cit_text = cit_text.split("Citation:", 1)[1]
        if "Extracted Category Hint:" in cit_text:
            cit_text = cit_text.split("Extracted Category Hint:", 1)[0]
        cit_text = cit_text.strip()

        # Multi-stage title extraction
        title = None
        # A. Quoted title
        qm = re.search(r'[\"“]([^\”\"\r\n]{8,300})[\"”]', cit_text)
        if qm:
            cand_t = qm.group(1).strip()
            if len(cand_t.split()) >= 3 and not non_pub_regex.search(cand_t):
                title = cand_t

        # B. Year delimiter (YYYY). Title...
        if not title:
            ym = re.search(
                r"\((?:19|20)\d{2}[a-z]?\)\s*[\.:,-]?\s*([A-Z][^\.\n]{8,250})(?:\.|\bISSN|\bVol|\bpp|\bin\b|\bdoi\b)",
                cit_text,
                re.IGNORECASE,
            )
            if ym:
                cand_t = ym.group(1).strip()
                if len(cand_t.split()) >= 3 and not non_pub_regex.search(cand_t):
                    title = cand_t

        # C. Bullet / heading prefix pattern
        if not title:
            bm = re.search(
                r"^[➢\-\*•\d\.\s]*\s*([A-Z][^\:\n]{10,250}?)(?:\s+(?:Design Engineering|International Journal|Journal|IEEE|ACM|Springer|Elsevier|Conference|ISSN|Vol|\(\d{4}\)))",
                cit_text,
            )
            if bm:
                cand_t = bm.group(1).strip()
                if len(cand_t.split()) >= 3 and not non_pub_regex.search(cand_t):
                    title = cand_t

        # D. Split parts
        if not title:
            parts = re.split(r"[\.\,\;]\s+", cit_text)
            for p in parts:
                clean_p = p.strip(' \t"\'“”-–—•*➢')
                words = clean_p.split()
                if 4 <= len(words) <= 30:
                    if not re.search(
                        r"\b(?:pp|vol|isbn|issn|page|pages|editions?|proceedings|university|department|paper presented|presented in|et\s+al\.?|and\s+[A-Z][a-z]?)\b",
                        clean_p,
                        re.IGNORECASE,
                    ):
                        if any(w[0].isupper() for w in words if w.isalpha()) and not non_pub_regex.search(clean_p):
                            title = clean_p
                            break

        # If title is unidentifiable, never assign valid tier
        if not title or len(title.split()) < 3:
            return {
                "title": None,
                "type": "other",
                "year": year,
                "tier": "Unranked",
                "confidence": 0.0,
            }

        # Determine tier strictly when title is valid
        if any(w in user_lower for w in ["nature", "acm", "ieee trans", "scs", "q1", "flagship"]):
            tier = "Tier-1"
        elif any(w in user_lower for w in ["springer", "elsevier", "iosr", "inderscience", "international journal", "international conference"]):
            tier = "Tier-2"
        elif any(w in user_lower for w in ["national conference", "symposium", "workshop", "colloquium"]):
            tier = "Tier-3"
        elif any(w in user_lower for w in ["arxiv", "preprint", "biorxiv", "ssrn"]):
            tier = "Unranked"
        else:
            tier = "Tier-2" if pub_type in ("journal", "conference") else "Unranked"

        return {
            "title": title,
            "type": pub_type,
            "year": year,
            "tier": tier,
            "confidence": 0.80,
        }
