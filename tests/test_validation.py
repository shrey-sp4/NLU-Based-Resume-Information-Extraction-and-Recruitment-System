import unittest

from src.extraction.config import build_default_config
from src.extraction.models import PageStatus
from src.extraction.validation import compute_text_metrics, evaluate_text, normalize_text


class ValidationTests(unittest.TestCase):
    def test_normalize_text_collapses_noise(self) -> None:
        self.assertEqual(normalize_text("  Hello\tworld\n\n\nAgain "), "Hello world\n\nAgain")

    def test_metrics_are_basic_counts_only(self) -> None:
        metrics = compute_text_metrics("Resume\nJohn Doe\nExperience")
        self.assertGreaterEqual(metrics.word_count, 3)
        self.assertFalse(hasattr(metrics, "quality_score"))

    def test_usable_text_passes_stage2_validation(self) -> None:
        config = build_default_config()
        decision = evaluate_text(
            "John Doe\nComputer Science\nExperience in research and teaching.",
            config,
            page_number=1,
            page_count=1,
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.page_status, PageStatus.PASS_)
        self.assertEqual(decision.reason, "usable_text_extracted")

    def test_empty_text_is_routed_to_review(self) -> None:
        config = build_default_config()
        decision = evaluate_text("", config, page_number=1, page_count=1)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.page_status, PageStatus.REVIEW)
        self.assertEqual(decision.reason, "no_text_extracted")


if __name__ == "__main__":
    unittest.main()
