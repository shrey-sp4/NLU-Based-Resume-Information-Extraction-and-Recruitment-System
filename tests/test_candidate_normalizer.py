from __future__ import annotations

import unittest
from shortlisting.normalization.candidate_normalizer import CandidateNormalizer


class TestCandidateNormalizer(unittest.TestCase):
    """Focused regression tests for candidate name cleaning and section heading rejection."""

    def test_reject_section_headings_as_names(self):
        """Verify that section headings falsely extracted as names are rejected to empty string."""
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Work Experience"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Experience"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Work History"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Employment History"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Professional Experience"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Education"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Publications"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Technical Skills"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Personal Details"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Contact Details"), "")

    def test_strip_cv_and_document_prefixes(self):
        """Verify that CV-, Resume-, and title prefixes are safely stripped while preserving candidate name."""
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("CV-Dr Soumen Mukherjee"),
            "Soumen Mukherjee",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("CV-Anurag Choudhary"),
            "Anurag Choudhary",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("CV_Amit Parikh"),
            "Amit Parikh",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("Curriculum Vitae - Rakesh Bhatnagar"),
            "Rakesh Bhatnagar",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("Resume - Isha Sharma"),
            "Isha Sharma",
        )

    def test_strip_credentials_and_titles(self):
        """Verify credential suffixes and academic titles are stripped cleanly."""
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("Dr. Amit Kumar, Ph.D."),
            "Amit Kumar",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("Prof. Snehamoy Pramanik, SMIEEE"),
            "Snehamoy Pramanik",
        )
        self.assertEqual(
            CandidateNormalizer.clean_candidate_name("Dr. Priya Ranjan Sahoo Post-doc"),
            "Priya Ranjan Sahoo",
        )

    def test_reject_invalid_and_non_person_text(self):
        """Verify non-person words, sentences, single words, and departments are rejected."""
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Department of Mathematics"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("Dedicated professional seeking opportunities"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("SingleName"), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name(""), "")
        self.assertEqual(CandidateNormalizer.clean_candidate_name("English Hindi Bengali"), "")


if __name__ == "__main__":
    unittest.main()
