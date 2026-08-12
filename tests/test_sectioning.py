import json
import tempfile
import unittest
from pathlib import Path

from src.sectioning.candidates import generate_heading_candidates
from src.sectioning.detector import SectionBoundaryDetector
from src.sectioning.features import extract_line_features
from src.sectioning.models import RawLineRecord, validate_annotation_record, validate_section_label
from src.sectioning.normalization import SectionNormalizer
from src.sectioning.output import build_annotation_records_from_run
from src.sectioning.segmenter import SectionSegmenter


class SectioningFeatureTests(unittest.TestCase):
    def test_extract_line_features(self) -> None:
        features = extract_line_features("Professional Experience", preceded_by_blank=True, followed_by_blank=True)
        self.assertEqual(features["char_count"], 23.0)
        self.assertEqual(features["word_count"], 2.0)
        self.assertEqual(features["preceded_by_blank"], 1.0)
        self.assertEqual(features["followed_by_blank"], 1.0)
        self.assertEqual(features["short_line"], 1.0)

    def test_candidate_generation_marks_heading_like_line(self) -> None:
        line = RawLineRecord(
            resume_id="r1",
            document_id="d1",
            source_file="f.pdf",
            source_run_id="run1",
            page_number=1,
            line_number=10,
            line_index=10,
            text="Professional Experience",
            preceded_by_blank=True,
            followed_by_blank=True,
        )
        candidate = generate_heading_candidates([line])[0]
        self.assertTrue(candidate.is_candidate)
        self.assertEqual(candidate.suggested_label, "experience")
        self.assertGreater(candidate.heading_score, 0.5)

    def test_section_label_validation(self) -> None:
        self.assertTrue(validate_section_label("experience"))
        self.assertFalse(validate_section_label("not_a_label"))

    def test_annotation_schema_validation(self) -> None:
        validate_annotation_record(
            {
                "resume_id": "r1",
                "page_number": 1,
                "line_number": 2,
                "text": "Experience",
                "is_heading": True,
                "section_label": "experience",
            }
        )
        with self.assertRaises(ValueError):
            validate_annotation_record(
                {
                    "resume_id": "r1",
                    "page_number": 1,
                    "line_number": 2,
                    "text": "Experience",
                    "is_heading": True,
                    "section_label": "bad_label",
                }
            )

    def test_normalizer_prefers_semantic_label(self) -> None:
        normalizer = SectionNormalizer()
        result = normalizer.normalize("Academic Background")
        self.assertEqual(result.canonical_section, "education")
        self.assertFalse(result.review_required)

    def test_detector_and_segmenter(self) -> None:
        lines = [
            RawLineRecord(
                resume_id="r1",
                document_id="d1",
                source_file="f.pdf",
                source_run_id="run1",
                page_number=1,
                line_number=1,
                line_index=1,
                text="Professional Experience",
                preceded_by_blank=True,
                followed_by_blank=True,
            ),
            RawLineRecord(
                resume_id="r1",
                document_id="d1",
                source_file="f.pdf",
                source_run_id="run1",
                page_number=1,
                line_number=2,
                line_index=2,
                text="Data Scientist at Example Co",
            ),
            RawLineRecord(
                resume_id="r1",
                document_id="d1",
                source_file="f.pdf",
                source_run_id="run1",
                page_number=1,
                line_number=3,
                line_index=3,
                text="Skills",
                preceded_by_blank=True,
                followed_by_blank=True,
            ),
            RawLineRecord(
                resume_id="r1",
                document_id="d1",
                source_file="f.pdf",
                source_run_id="run1",
                page_number=1,
                line_number=4,
                line_index=4,
                text="Python, SQL, NLP",
            ),
        ]
        detector = SectionBoundaryDetector()
        segmenter = SectionSegmenter(detector=detector)
        artifact = segmenter.segment(lines)
        self.assertGreaterEqual(len(artifact.result.sections), 2)
        self.assertIn(artifact.result.sections[0].section, {"experience", "other"})

    def test_annotation_dataset_builder_from_fake_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run_test"
            page_dir = run_dir / "documents" / "doc1" / "pages" / "page_0001"
            page_dir.mkdir(parents=True, exist_ok=True)
            page_payload = {
                "page_number": 1,
                "status": "PASS",
                "final_method": "native_pymupdf",
                "final_text": "Professional Experience\nData Scientist at Example Co\nSkills\nPython, SQL, NLP",
                "metrics": {},
                "attempts": [],
                "review_reason": None,
                "page_type_guess": "text",
            }
            (page_dir / "page.json").write_text(json.dumps(page_payload), encoding="utf-8")

            records = build_annotation_records_from_run(run_dir)
            self.assertGreaterEqual(len(records), 4)
            self.assertEqual(records[0].machine_suggested_section, "experience")


if __name__ == "__main__":
    unittest.main()
