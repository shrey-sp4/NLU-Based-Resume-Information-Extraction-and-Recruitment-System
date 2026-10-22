from __future__ import annotations

import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
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
    Provider-configurable LLM client supporting Google Gemini (primary),
    OpenAI, and deterministic offline heuristic mode.
    Uses standard library urllib for network transport without external dependencies.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: float = 15.0,
    ):
        # Determine provider: default to 'gemini' if GEMINI_API_KEY is present, else 'heuristic'
        env_provider = os.getenv("LLM_PROVIDER")
        if provider:
            self.provider = provider.lower()
        elif env_provider:
            self.provider = env_provider.lower()
        elif os.getenv("GEMINI_API_KEY"):
            self.provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
        else:
            self.provider = "heuristic"

        # Determine model name
        if model_name:
            self.model_name = model_name
        else:
            env_model = os.getenv("LLM_MODEL_NAME")
            if env_model:
                self.model_name = env_model
            elif self.provider == "gemini":
                self.model_name = "gemini-1.5-flash"
            elif self.provider == "openai":
                self.model_name = "gpt-4o-mini"
            else:
                self.model_name = "heuristic-deterministic"

        # Determine API key
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY")
            or ""
        )

        # Base URL for custom endpoints / proxies
        self.api_base = (api_base or os.getenv("LLM_API_BASE", "")).rstrip("/")
        self.timeout = timeout
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
            return dict(self._cache[cache_key])

        if self.provider == "gemini" and self.api_key:
            result = self._call_gemini(system_prompt, user_prompt)
        elif self.provider == "openai" and self.api_key:
            result = self._call_openai(system_prompt, user_prompt)
        else:
            result = self._fallback_heuristic(system_prompt, user_prompt)

        self._cache[cache_key] = result
        return dict(result)

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Makes a structured JSON generation call to Google Gemini API using urllib."""
        if self.api_base:
            url = f"{self.api_base}/v1beta/models/{self.model_name}:generateContent"
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

        full_url = f"{url}?key={urllib.parse.quote(self.api_key)}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\nTask Input:\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json",
            },
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            full_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    return self._build_error_fallback(
                        system_prompt, user_prompt, "Gemini returned zero candidates"
                    )
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                parsed = self._extract_json_block(raw_text)
                if not isinstance(parsed, dict):
                    return self._build_error_fallback(
                        system_prompt, user_prompt, "Gemini output did not parse into JSON object"
                    )
                parsed["_source"] = "gemini"
                parsed["_is_fallback"] = False
                return parsed

        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8")
            except Exception:
                pass
            return self._build_error_fallback(
                system_prompt, user_prompt, f"Gemini HTTP {exc.code} {exc.reason}: {err_body[:200]}"
            )
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"Gemini connection/timeout error: {exc}"
            )
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"Gemini response parsing error: {exc}"
            )
        except Exception as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"Gemini unexpected error: {exc}"
            )

    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Makes a structured JSON completion call to OpenAI API using urllib."""
        if self.api_base:
            url = f"{self.api_base}/chat/completions"
        else:
            url = "https://api.openai.com/v1/chat/completions"

        payload = {
            "model": self.model_name or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))
                choices = data.get("choices", [])
                if not choices:
                    return self._build_error_fallback(
                        system_prompt, user_prompt, "OpenAI returned zero choices"
                    )
                raw_text = choices[0].get("message", {}).get("content", "")
                parsed = self._extract_json_block(raw_text)
                if not isinstance(parsed, dict):
                    return self._build_error_fallback(
                        system_prompt, user_prompt, "OpenAI output did not parse into JSON object"
                    )
                parsed["_source"] = "openai"
                parsed["_is_fallback"] = False
                return parsed

        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8")
            except Exception:
                pass
            return self._build_error_fallback(
                system_prompt, user_prompt, f"OpenAI HTTP {exc.code} {exc.reason}: {err_body[:200]}"
            )
        except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"OpenAI connection/timeout error: {exc}"
            )
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"OpenAI response parsing error: {exc}"
            )
        except Exception as exc:
            return self._build_error_fallback(
                system_prompt, user_prompt, f"OpenAI unexpected error: {exc}"
            )

    def _build_error_fallback(
        self, system_prompt: str, user_prompt: str, error_msg: str
    ) -> Dict[str, Any]:
        """
        Builds safe fallback result upon API error or network failure.
        Never pretends the result came from an LLM; explicitly marks _is_fallback=True,
        assigns tier Unknown/Unranked with zero confidence, and logs failure rationale.
        """
        user_lower = user_prompt.lower()
        if "institution:" in user_lower:
            return {
                "tier": "Unknown",
                "confidence": 0.0,
                "reason": f"API error fallback ({error_msg})",
                "_source": "api_error_fallback",
                "_is_fallback": True,
            }

        # Publication query
        from shortlisting.normalization.publication_normalizer import PublicationNormalizer

        cit_text = user_prompt
        hint = ""
        if "Citation:" in cit_text:
            cit_text = cit_text.split("Citation:", 1)[1]
        if "Extracted Category Hint:" in cit_text:
            parts = cit_text.split("Extracted Category Hint:", 1)
            cit_text = parts[0]
            hint = parts[1].strip()
        cit_text = cit_text.strip()

        title = PublicationNormalizer._extract_title(cit_text)
        year = PublicationNormalizer._extract_year(cit_text)
        pub_type = PublicationNormalizer._determine_type(hint, cit_text)

        return {
            "title": title,
            "type": pub_type,
            "year": year,
            "tier": "Unranked",
            "confidence": 0.0,
            "reason": f"API error fallback ({error_msg})",
            "_source": "api_error_fallback",
            "_is_fallback": True,
        }

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
                return {
                    "tier": "Unknown",
                    "confidence": 0.0,
                    "reason": "Not an educational institution.",
                    "_source": "offline_fallback",
                    "_is_fallback": True,
                }

            if any(k in user_lower for k in ["national importance", "institute of technology", "central university", "premier", "iit", "nit", "iim", "iisc"]):
                return {
                    "tier": "Tier-1",
                    "confidence": 0.85,
                    "reason": "Institution recognized as apex / national research importance.",
                    "_source": "offline_fallback",
                    "_is_fallback": True,
                }
            elif any(k in user_lower for k in ["state university", "deemed university", "university", "autonomous", "vishwavidyalaya"]):
                return {
                    "tier": "Tier-2",
                    "confidence": 0.75,
                    "reason": "Recognized state or autonomous university entity.",
                    "_source": "offline_fallback",
                    "_is_fallback": True,
                }
            elif any(k in user_lower for k in ["college", "school", "vidyalaya", "institute"]):
                return {
                    "tier": "Tier-3",
                    "confidence": 0.65,
                    "reason": "Affiliated college or local educational institute.",
                    "_source": "offline_fallback",
                    "_is_fallback": True,
                }
            else:
                return {
                    "tier": "Unknown",
                    "confidence": 0.30,
                    "reason": "Institutional information ambiguous or unrecognized.",
                    "_source": "offline_fallback",
                    "_is_fallback": True,
                }

        # Case 2: Publication Citation Query
        from shortlisting.normalization.publication_normalizer import PublicationNormalizer

        # Isolate citation text from hint and prompt wrappers
        cit_text = user_prompt
        hint = ""
        if "Citation:" in cit_text:
            cit_text = cit_text.split("Citation:", 1)[1]
        if "Extracted Category Hint:" in cit_text:
            parts = cit_text.split("Extracted Category Hint:", 1)
            cit_text = parts[0]
            hint = parts[1].strip()
        cit_text = cit_text.strip()

        if PublicationNormalizer._is_invalid_citation(cit_text):
            return {
                "title": None,
                "type": "other",
                "year": None,
                "tier": "Unranked",
                "confidence": 0.0,
                "_source": "offline_fallback",
                "_is_fallback": True,
            }

        title = PublicationNormalizer._extract_title(cit_text)
        if not title or (len(title.split()) < 3 and len(title) < 20) or PublicationNormalizer._is_invalid_citation(title):
            return {
                "title": None,
                "type": "other",
                "year": None,
                "tier": "Unranked",
                "confidence": 0.0,
                "_source": "offline_fallback",
                "_is_fallback": True,
            }

        year = PublicationNormalizer._extract_year(cit_text)
        pub_type = PublicationNormalizer._determine_type(hint, cit_text)

        # Do not invent tiers in offline heuristic fallback; return Unranked
        return {
            "title": title,
            "type": pub_type,
            "year": year,
            "tier": "Unranked",
            "confidence": 0.0,
            "_source": "offline_fallback",
            "_is_fallback": True,
        }


