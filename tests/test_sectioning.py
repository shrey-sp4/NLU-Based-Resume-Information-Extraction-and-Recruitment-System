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
    def setUp(self) -> None:
        self.normalizer = SectionNormalizer()
        self.detector = SectionBoundaryDetector(normalizer=self.normalizer)
        self.segmenter = SectionSegmenter(detector=self.detector, normalizer=self.normalizer)

    def test_extract_line_features(self) -> None:
        features = extract_line_features("Professional Experience", preceded_by_blank=True, followed_by_blank=True)
        self.assertEqual(features["char_count"], 23.0)
        self.assertEqual(features["word_count"], 2.0)
        self.assertEqual(features["preceded_by_blank"], 1.0)

    def test_1_canonical_top_level_section(self) -> None:
        res = self.normalizer.normalize("EDUCATION")
        self.assertEqual(res.canonical_section, "education")
        line = RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "EDUCATION", preceded_by_blank=True)
        dec = self.detector.predict_line(line, previous_blank=True)
        self.assertTrue(dec.is_heading)
        self.assertEqual(dec.canonical_section, "education")

    def test_2_canonical_section_with_subsection(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "PUBLICATIONS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Main publication list text"),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "Research Articles:", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 4, 4, "1. Article title..."),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(len(spans), 2)
        # Parent section
        self.assertEqual(spans[0].normalized_heading, "publications")
        self.assertEqual(spans[0].level, 1)
        self.assertEqual(spans[0].section_type, "canonical")

        # Subsection
        self.assertEqual(spans[1].original_heading, "Research Articles:")
        self.assertEqual(spans[1].level, 2)
        self.assertEqual(spans[1].section_type, "subsection")
        self.assertEqual(spans[1].parent_section_id, spans[0].section_id)

    def test_3_multiple_subsections_under_one_parent(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "PUBLICATIONS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Research Articles:", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "Refereed Manuscripts:", preceded_by_blank=True),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[1].parent_section_id, spans[0].section_id)
        self.assertEqual(spans[2].parent_section_id, spans[0].section_id)

    def test_4_sibling_custom_top_level_sections(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "DECLARATION", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Declaration body..."),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "REMARKS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 4, 4, "Remarks body..."),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(spans[0].section_type, "custom")
        self.assertEqual(spans[0].level, 1)
        self.assertIsNone(spans[0].parent_section_id)

        self.assertEqual(spans[1].section_type, "custom")
        self.assertEqual(spans[1].level, 1)
        self.assertIsNone(spans[1].parent_section_id)

    def test_5_uncertain_parent_relationship(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "PUBLICATIONS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "MISCELLANEOUS ATTAINMENTS", preceded_by_blank=True),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(spans[1].section_type, "custom")
        self.assertEqual(spans[1].level, 1)
        self.assertIsNone(spans[1].parent_section_id)


    def test_6_repeated_canonical_section(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "WORK EXPERIENCE", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Role 1"),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "WORK EXPERIENCE", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 4, 4, "Role 2"),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0].normalized_heading, "experience")
        self.assertEqual(spans[1].normalized_heading, "experience")
        self.assertNotEqual(spans[0].section_id, spans[1].section_id)

    def test_7_repeated_section_not_duplicate_span(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "SKILLS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Python, SQL"),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "SKILLS", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 4, 4, "Git, Docker"),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertNotEqual(spans[0].start_line, spans[1].start_line)

    def test_8_genuinely_overlapping_spans_detector(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, i, i, f"Line {i}")
            for i in range(1, 10)
        ]
        artifact = self.segmenter.segment(lines)
        indices = [l["line_index"] for span in artifact.result.sections for l in span.to_dict()["lines"]]
        self.assertEqual(len(indices), len(set(indices)))

    def test_9_contact_vs_preamble(self) -> None:
        lines = [
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 1, 1, "John Smith"),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 2, 2, "Pre-heading top header"),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 3, 3, "EDUCATION", preceded_by_blank=True),
            RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 4, 4, "Degree info"),
        ]
        artifact = self.segmenter.segment(lines)
        spans = artifact.result.sections
        self.assertEqual(spans[0].section_type, "preamble")
        self.assertEqual(spans[0].normalized_heading, "preamble")
        self.assertEqual(spans[0].original_heading, "")

    def test_10_custom_heading_preservation(self) -> None:
        res = self.normalizer.normalize("SPECIAL AWARDS & HONORS")
        self.assertEqual(res.canonical_section, "awards")

    def test_11_complete_text_coverage(self) -> None:
        lines = [RawLineRecord("r1", "d1", "f.pdf", "run1", 1, i, i, f"Text line {i}") for i in range(1, 20)]
        artifact = self.segmenter.segment(lines)
        total_spanned = sum(len(span.lines) for span in artifact.result.sections)
        self.assertEqual(total_spanned, 19)
        self.assertEqual(artifact.result.summary["text_coverage_ratio"], 1.0)

    def test_12_no_duplicated_text(self) -> None:
        lines = [RawLineRecord("r1", "d1", "f.pdf", "run1", 1, i, i, f"Unique text line {i}") for i in range(1, 10)]
        artifact = self.segmenter.segment(lines)
        texts = [l["text"] for span in artifact.result.sections for l in span.to_dict()["lines"]]
        self.assertEqual(len(texts), 9)

    def test_13_body_sentence_rejection(self) -> None:
        sentence = "Developed deep learning models using Python and PyTorch for text parsing."
        line = RawLineRecord("r1", "d1", "f.pdf", "run1", 1, 5, 5, sentence, preceded_by_blank=True)
        dec = self.detector.predict_line(line, previous_blank=True)
        self.assertFalse(dec.is_heading)


if __name__ == "__main__":
    unittest.main()
