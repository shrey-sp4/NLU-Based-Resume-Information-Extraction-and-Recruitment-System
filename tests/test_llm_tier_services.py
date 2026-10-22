from __future__ import annotations

import io
import json
import socket
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from shortlisting.llm.client import ConfigurableLLMClient
from shortlisting.llm.publication_service import PublicationService
from shortlisting.llm.university_tier_service import UniversityTierService


class TestLLMTierServices(unittest.TestCase):
    """
    Comprehensive tests for provider-configurable LLM integration,
    Google Gemini support, offline heuristic fallback, error handling,
    and schema enforcement.
    """

    def setUp(self):
        # Clear cached client instances between tests if any
        pass

    def test_offline_mode_without_api_credentials(self):
        """Verify deterministic fallback when no credentials exist or provider is offline/heuristic."""
        with patch.dict("os.environ", {}, clear=True):
            client = ConfigurableLLMClient(provider="heuristic", api_key="")
            self.assertEqual(client.provider, "heuristic")
            self.assertFalse(client.api_key)

            # 1. Institution tiering fallback
            res_iit = client.generate_json("System prompt", "Institution: Indian Institute of Technology Bombay")
            self.assertEqual(res_iit["tier"], "Tier-1")
            self.assertTrue(res_iit["_is_fallback"])
            self.assertEqual(res_iit["_source"], "offline_fallback")

            # 2. Table header rejection
            res_header = client.generate_json("System prompt", "Institution: Degree University Percentage")
            self.assertEqual(res_header["tier"], "Unknown")
            self.assertEqual(res_header["confidence"], 0.0)

            # 3. Publication citation fallback - must return Unranked
            res_pub = client.generate_json(
                "System prompt",
                "Citation: P. Ghosh, 'Quantum Error Correction in Practice', Physical Review Letters, 2021",
            )
            self.assertEqual(res_pub["tier"], "Unranked")
            self.assertTrue(res_pub["_is_fallback"])
            self.assertEqual(res_pub["title"], "Quantum Error Correction in Practice")
            self.assertEqual(res_pub["year"], "2021")

    def test_gemini_successful_response_parsing(self):
        """Verify successful Gemini API response parsing with markdown code fences."""
        mock_response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "```json\n{\n  \"tier\": \"Tier-1\",\n  \"confidence\": 0.95,\n  \"reason\": \"Apex national institute of technology with premier doctoral research.\"\n}\n```"
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp_bytes = json.dumps(mock_response_payload).encode("utf-8")

        mock_http_resp = MagicMock()
        mock_http_resp.read.return_value = mock_resp_bytes
        mock_http_resp.__enter__.return_value = mock_http_resp

        with patch("urllib.request.urlopen", return_value=mock_http_resp) as mock_urlopen:
            client = ConfigurableLLMClient(
                provider="gemini",
                model_name="gemini-1.5-flash",
                api_key="test-gemini-key-12345",
            )
            svc = UniversityTierService(llm_client=client)
            result = svc.categorize_institution("DA-IICT Gandhinagar")

            self.assertEqual(result["tier"], "Tier-1")
            self.assertEqual(result["confidence"], 0.95)
            self.assertEqual(result["source"], "gemini")
            self.assertIn("Apex national institute", result["reason"])

            # Verify urllib request parameters
            self.assertEqual(mock_urlopen.call_count, 1)
            req = mock_urlopen.call_args[0][0]
            self.assertIn("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent", req.full_url)
            self.assertIn("key=test-gemini-key-12345", req.full_url)
            sent_body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(sent_body["generationConfig"]["responseMimeType"], "application/json")

    def test_gemini_malformed_response_handling(self):
        """Verify that malformed or non-JSON Gemini responses fall back gracefully without crashing."""
        mock_response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "I am unable to classify this institution due to missing details."}
                        ]
                    }
                }
            ]
        }
        mock_resp_bytes = json.dumps(mock_response_payload).encode("utf-8")

        mock_http_resp = MagicMock()
        mock_http_resp.read.return_value = mock_resp_bytes
        mock_http_resp.__enter__.return_value = mock_http_resp

        with patch("urllib.request.urlopen", return_value=mock_http_resp):
            client = ConfigurableLLMClient(provider="gemini", api_key="test-key")
            svc = UniversityTierService(llm_client=client)
            result = svc.categorize_institution("Indian Institute of Science")

            # Must fall back gracefully to Unknown with zero confidence, never crashing
            self.assertEqual(result["tier"], "Unknown")
            self.assertEqual(result["confidence"], 0.0)
            self.assertIn("API error fallback", result["reason"])
            self.assertEqual(result["source"], "api_error_fallback")

    def test_gemini_rate_limit_and_server_error_handling(self):
        """Verify that HTTP 429 (rate limit) and HTTP 503 (service unavailable) trigger safe fallbacks."""
        # 1. Test HTTP 429 Rate Limit
        http_429 = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"code": 429, "message": "Resource exhausted"}}'),
        )
        with patch("urllib.request.urlopen", side_effect=http_429):
            client = ConfigurableLLMClient(provider="gemini", api_key="test-key")
            svc = UniversityTierService(llm_client=client)
            result = svc.categorize_institution("University of Delhi")

            self.assertEqual(result["tier"], "Unknown")
            self.assertEqual(result["confidence"], 0.0)
            self.assertIn("HTTP 429", result["reason"])
            self.assertEqual(result["source"], "api_error_fallback")

        # 2. Test HTTP 503 Service Unavailable
        http_503 = urllib.error.HTTPError(
            url="https://generativelanguage.googleapis.com",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"error": {"code": 503, "message": "Backend unavailable"}}'),
        )
        with patch("urllib.request.urlopen", side_effect=http_503):
            client = ConfigurableLLMClient(provider="gemini", api_key="test-key")
            svc = UniversityTierService(llm_client=client)
            result = svc.categorize_institution("Jadavpur University")

            self.assertEqual(result["tier"], "Unknown")
            self.assertEqual(result["confidence"], 0.0)
            self.assertIn("HTTP 503", result["reason"])

    def test_gemini_socket_timeout_handling(self):
        """Verify that network socket timeout triggers safe fallback without stalling."""
        with patch("urllib.request.urlopen", side_effect=socket.timeout("The read operation timed out")):
            client = ConfigurableLLMClient(provider="gemini", api_key="test-key", timeout=1.0)
            svc = UniversityTierService(llm_client=client)
            result = svc.categorize_institution("Banaras Hindu University")

            self.assertEqual(result["tier"], "Unknown")
            self.assertEqual(result["confidence"], 0.0)
            self.assertIn("connection/timeout error", result["reason"])

    def test_university_tier_strictly_independent_from_candidate_degree(self):
        """
        Verify that UniversityTierService evaluates solely the institution entity.
        Degree, name, experience, or other candidate credentials must NEVER be included
        in the classification prompt sent to the LLM client.
        """
        captured_prompts = []

        class SpyLLMClient(ConfigurableLLMClient):
            def generate_json(self, system_prompt: str, user_prompt: str):
                captured_prompts.append(user_prompt)
                return {"tier": "Tier-1", "confidence": 0.9, "reason": "Verified", "_source": "gemini", "_is_fallback": False}

        spy = SpyLLMClient()
        svc = UniversityTierService(llm_client=spy)

        # Call with different degree contexts
        svc.categorize_institution("Indian Institute of Technology Kharagpur", degree="Ph.D. in Computer Science")
        svc.categorize_institution("Indian Institute of Technology Kharagpur", degree="Bachelor of Technology")
        svc.categorize_institution("Indian Institute of Technology Kharagpur", degree="Matriculation Secondary High School")
        svc.categorize_institution("Indian Institute of Technology Kharagpur", degree="")

        self.assertEqual(len(captured_prompts), 4)
        for p in captured_prompts:
            self.assertEqual(p, "Institution: Indian Institute of Technology Kharagpur")
            self.assertNotIn("Ph.D", p)
            self.assertNotIn("Bachelor", p)
            self.assertNotIn("Matriculation", p)
            self.assertNotIn("Degree:", p)

    def test_publication_schema_and_no_leakage_on_api_call(self):
        """
        Verify that PublicationService returns strictly {title, type, year, tier}
        and never leaks venue, DOI, or raw citation strings, even if returned by LLM.
        """
        mock_response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "title": "Robust Sequence Labeling for Resumes",
                                    "type": "conference",
                                    "year": "2023",
                                    "tier": "Tier-1",
                                    "venue": "ACL 2023",
                                    "doi": "10.18653/v1/2023.acl-long.123",
                                    "raw_citation": "Full citation string that must never leak",
                                })
                            }
                        ]
                    }
                }
            ]
        }
        mock_resp_bytes = json.dumps(mock_response_payload).encode("utf-8")

        mock_http_resp = MagicMock()
        mock_http_resp.read.return_value = mock_resp_bytes
        mock_http_resp.__enter__.return_value = mock_http_resp

        with patch("urllib.request.urlopen", return_value=mock_http_resp):
            client = ConfigurableLLMClient(provider="gemini", api_key="test-key")
            pub_svc = PublicationService(llm_client=client)

            res = pub_svc.parse_and_classify_citation(
                "A. Author, 'Robust Sequence Labeling for Resumes', ACL, 2023. DOI: 10.18653/v1/2023.acl-long.123",
                category_hint="conference",
            )

            # Strict recruiter schema validation
            self.assertEqual(set(res.keys()), {"title", "type", "year", "tier"})
            self.assertEqual(res["title"], "Robust Sequence Labeling for Resumes")
            self.assertEqual(res["type"], "conference")
            self.assertEqual(res["year"], "2023")
            self.assertEqual(res["tier"], "Tier-1")
            self.assertNotIn("venue", res)
            self.assertNotIn("doi", res)
            self.assertNotIn("raw_citation", res)

    def test_environment_configuration_precedence(self):
        """Verify environment variable configuration for Gemini provider and model."""
        test_env = {
            "GEMINI_API_KEY": "env-gemini-secret-key",
            "LLM_MODEL_NAME": "gemini-1.5-flash",
            "LLM_API_BASE": "https://custom-proxy.internal",
        }
        with patch.dict("os.environ", test_env, clear=True):
            client = ConfigurableLLMClient()
            self.assertEqual(client.provider, "gemini")
            self.assertEqual(client.model_name, "gemini-1.5-flash")
            self.assertEqual(client.api_key, "env-gemini-secret-key")
            self.assertEqual(client.api_base, "https://custom-proxy.internal")


if __name__ == "__main__":
    unittest.main()
