from __future__ import annotations

import unittest
from pathlib import Path

from src.ner.extractors import HybridEntityExtractor
from src.ner.gazetteers import is_in_degree_gazetteer, is_in_skill_gazetteer
from src.ner.models import ExtractedEntity, CandidateProfile


class TestStage4NER(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = HybridEntityExtractor()

    def test_deterministic_email_extraction(self) -> None:
        line_text = "Contact me at mitesh.solanki@example.com for queries."
        entities = self.extractor.extract_deterministic_entities(
            line_text, page_num=1, line_num=1, line_idx=1, sec_id="sec_001", sec_type="contact"
        )
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].value, "mitesh.solanki@example.com")
        self.assertEqual(entities[0].entity_type, "email")
        self.assertEqual(line_text[entities[0].start_char:entities[0].end_char], "mitesh.solanki@example.com")

    def test_deterministic_phone_extraction(self) -> None:
        line_text = "Phone: +91 9427373948"
        entities = self.extractor.extract_deterministic_entities(
            line_text, page_num=1, line_num=2, line_idx=2, sec_id="sec_001", sec_type="contact"
        )
        self.assertEqual(len(entities), 1)
        self.assertIn("9427373948", entities[0].value)

    def test_gazetteer_skill_matching(self) -> None:
        self.assertTrue(is_in_skill_gazetteer("Python"))
        self.assertTrue(is_in_skill_gazetteer("Docker"))
        self.assertFalse(is_in_skill_gazetteer("RandomWord123"))

    def test_gazetteer_degree_matching(self) -> None:
        self.assertTrue(is_in_degree_gazetteer("B.Tech"))
        self.assertTrue(is_in_degree_gazetteer("Ph.D."))

    def test_conflict_resolution_precedence(self) -> None:
        e1 = ExtractedEntity(
            value="mitesh@example.com",
            entity_type="email",
            confidence=1.0,
            source_section_id="sec_1",
            source_section_type="contact",
            page_number=1,
            line_number=1,
            line_index=1,
            start_char=0,
            end_char=18,
            raw_line_text="mitesh@example.com",
            extractor_name="deterministic_regex",
        )
        e2 = ExtractedEntity(
            value="mitesh@example.com",
            entity_type="name",
            confidence=0.7,
            source_section_id="sec_1",
            source_section_type="contact",
            page_number=1,
            line_number=1,
            line_index=1,
            start_char=0,
            end_char=18,
            raw_line_text="mitesh@example.com",
            extractor_name="learned_crf_ner",
        )
        resolved, conflicts = self.extractor.resolve_conflicts([e1, e2])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].entity_type, "email")
        self.assertEqual(conflicts, 1)


if __name__ == "__main__":
    unittest.main()
