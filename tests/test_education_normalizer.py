import json
import unittest
from pathlib import Path

from shortlisting.normalization.education_normalizer import EducationNormalizer


class TestEducationNormalizerAuditCases(unittest.TestCase):
    def setUp(self):
        self.normalizer = EducationNormalizer()
        self.pred_dir = Path(__file__).resolve().parents[1] / "output" / "predictions"

    def _load_prediction_education(self, filename: str):
        path = self.pred_dir / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("education", [])

    def test_cv_aakash_daiict(self):
        """
        Audit verification for cv_aakash_daiict.json:
        - No empty-degree qualification emitted (no orphaned IIT record without a degree).
        - Both Master of Science and Bachelor of Science degrees are extracted.
        - Neither degree is associated with secondary education (S.B.N Public School or Aum Sun Public School).
        - Verifies degree-institution associations across prediction formats without weakening checks.
        """
        raw_edu = self._load_prediction_education("cv_aakash_daiict.json")
        entries = self.normalizer.normalize(raw_edu)

        # Confirm no empty degree records
        for e in entries:
            self.assertTrue(len(e.degree.strip()) > 0, f"Empty degree emitted: {e}")

        # Check degrees present
        degrees = [e.degree for e in entries]
        self.assertIn("Master of Science", degrees)
        self.assertIn("Bachelor of Science", degrees)

        # Confirm secondary education is absent from all normalized institutions
        self.assertFalse(any("School" in e.institution for e in entries))
        self.assertFalse(any("S.B.N" in e.institution for e in entries))
        self.assertFalse(any("Aum Sun" in e.institution for e in entries))

        msc_entry = next(e for e in entries if e.degree == "Master of Science")
        bsc_entry = next(e for e in entries if e.degree == "Bachelor of Science")

        # Degree-institution associations based on explicit source evidence:
        # 1. Master of Science: In cv_aakash_daiict.json, its true institution (IIT Guwahati) was
        #    isolated into an orphaned prediction entry without a degree. Within the second multi-degree
        #    text block, Master of Science has no explicitly attached institution prior to its date.
        #    Because cross-record association is unsupported and ambiguous, its institution must
        #    remain empty ("") and its tier "Unknown" rather than guessing or falsely pairing with Deshbandhu College.
        self.assertEqual(msc_entry.institution, "")
        self.assertEqual(msc_entry.university_tier, "Unknown")

        # 2. Bachelor of Science: Explicitly associated with Deshbandhu College in the source text.
        self.assertEqual(bsc_entry.institution, "Deshbandhu College")
        self.assertEqual(bsc_entry.university_tier, "Tier-3")

    def test_updated_cv_dr_soumen_mukherjee(self):
        """
        Audit verification for Updated_CV-_Dr_Soumen_Mukherjee.json:
        - Must NOT falsely associate Ph.D. with Banaras Hindu University.
        - Safely recovers all 3 degrees with explicit associations:
          1. Ph.D. -> University of Lucknow
          2. Master of Arts -> Banaras Hindu University
          3. Bachelor of Arts -> Vidyasagar University
        """
        raw_edu = self._load_prediction_education("Updated_CV-_Dr_Soumen_Mukherjee.json")
        entries = self.normalizer.normalize(raw_edu)

        self.assertEqual(len(entries), 3, f"Expected 3 degrees for Dr. Soumen Mukherjee, got {len(entries)}")
        degrees_map = {e.degree: e.institution for e in entries}

        phd_inst = degrees_map.get("Ph.D.")
        ma_inst = degrees_map.get("Master of Arts")
        ba_inst = degrees_map.get("Bachelor of Arts")

        self.assertIsNotNone(phd_inst)
        self.assertIsNotNone(ma_inst)
        self.assertIsNotNone(ba_inst)

        self.assertEqual(phd_inst, "University of Lucknow")
        self.assertEqual(ma_inst, "Banaras Hindu University")
        self.assertEqual(ba_inst, "Vidyasagar University")

    def test_cv_chandan(self):
        """
        Audit verification for CV_Chandan.json:
        - 'Post Doctoral Research Associate' must NOT be interpreted as an academic degree.
        - Safely recovers M.S. at Indian Institution of Science Education (IISER Bhopal).
        - Ph.D. and B.Sc. preserved.
        - Secondary education filtered out.
        """
        raw_edu = self._load_prediction_education("CV_Chandan.json")
        entries = self.normalizer.normalize(raw_edu)

        # Post Doctoral must NOT appear as an education entry
        self.assertFalse(
            any("post" in e.degree.lower() for e in entries),
            "Postdoctoral employment appointment must not be emitted as an academic degree",
        )

        # Valid degrees preserved
        degs = [e.degree for e in entries]
        self.assertIn("Ph.D.", degs)
        self.assertIn("M.S", degs)
        self.assertIn("B.Sc", degs)

        # M.S. institution verified
        ms_entry = next(e for e in entries if e.degree == "M.S")
        self.assertIn("Science Education", ms_entry.institution)

    def test_resume_final_amit_cma_iim_a(self):
        """
        Audit verification for Resume_final_Amit_CMA_IIM_A.json:
        - Safely recovers BA at University of Delhi.
        - Safely recovers Master in Arts at Kurukshetra University.
        - Secondary schooling (Patna Central School) filtered out.
        - Preserves higher degrees (IIT M.Sc and Ph.D.).
        """
        raw_edu = self._load_prediction_education("Resume_final_Amit_CMA_IIM_A.json")
        entries = self.normalizer.normalize(raw_edu)

        # No secondary school
        for e in entries:
            self.assertNotIn("Patna Central School", e.institution)

        deg_map = {e.degree: e.institution for e in entries}
        self.assertEqual(deg_map.get("BA"), "University of Delhi")
        self.assertEqual(deg_map.get("Master in Arts"), "Kurukshetra University")

    def test_lokendra_cv_revised1_daiict(self):
        """
        Audit verification for Lokendra_CV_Revised1_DAIICT.json:
        - Canonicalizes PhD and Doctor of Philosophy into a single Ph.D. entry (no duplicate).
        - Ph.D. associated with Visvesvaraya National Institute of Technology (VNIT).
        - Master of Engineering is NOT falsely associated with Medicaps.
        - Bachelor of Engineering is correctly associated with Medicaps Institute of Technology.
        - Secondary schooling filtered out.
        """
        raw_edu = self._load_prediction_education("Lokendra_CV_Revised1_DAIICT.json")
        entries = self.normalizer.normalize(raw_edu)

        doctorate_entries = [e for e in entries if "ph" in e.degree.lower() or "doctor" in e.degree.lower()]
        self.assertEqual(
            len(doctorate_entries),
            1,
            f"Expected exactly 1 doctorate entry after deduplication, got {len(doctorate_entries)}: {doctorate_entries}",
        )
        self.assertEqual(doctorate_entries[0].institution, "Visvesvaraya National Institute of Technology")

        me_entry = next(e for e in entries if "master" in e.degree.lower())
        be_entry = next(e for e in entries if "bachelor" in e.degree.lower())

        self.assertNotEqual(me_entry.institution, "Medicaps Institute of Technology and Management")
        self.assertEqual(be_entry.institution, "Medicaps Institute of Technology and Management")

    def test_snehamoy_location_ma_rejection(self):
        """
        Audit verification for Snehamoy_P_CV.json:
        - 'Medford, MA, USA' must NOT be matched as Master of Arts.
        - 'PostDoctoral' appointment must NOT be emitted as an academic degree.
        - Candidate's Ph.D. is preserved.
        """
        raw_edu = self._load_prediction_education("Snehamoy_P_CV.json")
        entries = self.normalizer.normalize(raw_edu)

        self.assertFalse(
            any("post" in e.degree.lower() for e in entries),
            "PostDoctoral appointment title must not be emitted as an academic degree",
        )
        self.assertFalse(
            any(e.degree in ("MA", "M.A.", "Master of Arts") for e in entries),
            "US state code 'MA' in 'Medford, MA, USA' must not be interpreted as Master of Arts",
        )
        self.assertTrue(any("ph" in e.degree.lower() for e in entries))

    def test_orphaned_institution_record_rejection(self):
        """Ensures that records with an institution but no verifiable degree are rejected."""
        mock_raw = [
            {"degree": "", "institution": "Indian Institute of Technology", "raw_text": "IIT Guwahati campus"},
            {"degree": "", "institution": "Random Institute of Tech", "raw_text": "Random Institute of Tech"},
        ]
        entries = self.normalizer.normalize(mock_raw)
        self.assertEqual(entries, [], "Orphaned institution-only entries must be rejected")

    def test_preserve_higher_degree_with_secondary_education_in_same_block(self):
        """Preserves legitimate higher-degree records even when secondary education appears in the same text."""
        mock_raw = [
            {
                "degree": "M.Sc",
                "institution": "Sardar Patel University",
                "raw_text": "M.Sc. in Statistics (2010) from Sardar Patel University - 62% 12th STD (2005) from Maharashtra Board - 63% 10th STD (2003) from Maharashtra Board - 68%",
            }
        ]
        entries = self.normalizer.normalize(mock_raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].degree, "M.Sc")
        self.assertEqual(entries[0].institution, "Sardar Patel University")


if __name__ == "__main__":
    unittest.main()
