from __future__ import annotations

import json
from pathlib import Path
import unittest

from shortlisting.normalization.publication_normalizer import PublicationNormalizer
from shortlisting.models.candidate import PublicationEntry


class TestPublicationNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = PublicationNormalizer()

    def test_cv_aakash_daiict_papers_preserved_and_clean(self):
        """Verify cv_aakash_daiict preserves all papers without author leak or false rejection on 'and k-normal'."""
        raw_pubs = {
            "journal_articles": [
                "Aakash Choudhary and R.K. Sharma: Existence of primitive pairs with two prescribed traces over finite fields, Journal of Algebra and Applications (2023). doi.org/10.1142/S0219498824502451",
                "Aakash Choudhary and R.K. Sharma: On pairs of r-primitive and k-normal elements with prescribed traces over finite fields. (Communicated)",
                "Aakash Choudhary and R.K. Sharma: Fields having arithmetic progression of r-primitive and k-normal elements with prescribed traces. (Communicated)",
                "Aakash Choudhary and R.K. Sharma: Fields having primitive pairs with prescribed norms, traces and primitive components. (Communicated)",
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        self.assertEqual(len(res), 4)

        titles = [e.title for e in res]
        self.assertIn("Existence of primitive pairs with two prescribed traces over finite fields", titles)
        self.assertIn("On pairs of r-primitive and k-normal elements with prescribed traces over finite fields", titles)
        self.assertIn("Fields having arithmetic progression of r-primitive and k-normal elements with prescribed traces", titles)
        self.assertIn("Fields having primitive pairs with prescribed norms, traces and primitive components", titles)

        # Ensure no author names or prefixes leaked into titles
        for t in titles:
            self.assertNotIn("Aakash Choudhary", t)
            self.assertNotIn("Sharma:", t)
            self.assertNotIn("R.K. Sharma", t)

        # Check year extraction: 2023 for first, None for Communicated
        first_entry = next(e for e in res if "Existence of primitive pairs" in e.title)
        self.assertEqual(first_entry.year, "2023")
        comm_entry = next(e for e in res if "k-normal elements" in e.title)
        self.assertIsNone(comm_entry.year)

    def test_soumen_mukherjee_preamble_and_book_and_split(self):
        """Verify summary preamble is stripped and genuine book/papers are extracted."""
        raw_pubs = {
            "journal_articles": [
                "A total of 43 publications [01 book; 16 Research Papers in Peer-Reviewed Journals (both Scopus & Non-Scopus); 04 Research Papers in books/edited volumes; 10 articles as Conference Proceedings, and12articles in Newspapers/Magazines/Newsletters/Periodicals /Souvenirs] AuthoredBook CV-DrSoumenMukherjee egaP 3 \uf076 Against All Odds: The struggle of the Marginalized in select Indian English Fiction, Foreword by-Dr. Kiran Mazumdar-Shaw (CMD-Biocon India Pvt. Ltd.), New Delhi: Raj Publications, Pub. March, 2015; ISBNNo.: 9789382281313 International(abroad):",
                "(i)“TheEmergence of Asiaas aGlobalLeader in theField of Higher Education”; (ii) “TheRole of InformationTechnologyin TeachingEnglish”, 'QS- Asia –Pacific Professional Leadersin Education–International Conference andExhibition', on theTheme ‘Asian Universities–Forgingpartnership ahead', Nanyang TechnologicalUniversity, Singapore,4th- 6th, Aug.2005.",
            ],
            "conference_papers": [
                "“Just try, you can also succeed!” How to write a good review paper in the domain of Humanities?”,11th International Mardin Artuklu online Conference on the theme- ‘Scientific CV-DrSoumenMukherjee egaP 9 Researches’, Institute of Economic Development and Social Research (IKSAD), Mardin, Turkey, 13th-15th Dec.,2023."
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        titles = [e.title for e in res]

        # Preamble must NOT be emitted as a title
        self.assertFalse(any("A total of 43 publications" in t for t in titles))

        # Authored book must be recovered with year 2015
        book_entry = next((e for e in res if "Against All Odds" in e.title), None)
        self.assertIsNotNone(book_entry)
        self.assertEqual(book_entry.title, "Against All Odds: The struggle of the Marginalized in select Indian English Fiction")
        self.assertEqual(book_entry.year, "2015")

        # Multi-item citation must be split
        self.assertTrue(any("TheEmergence of Asiaas aGlobalLeader" in t for t in titles))
        self.assertTrue(any("TheRole of InformationTechnologyin TeachingEnglish" in t for t in titles))

        # Conference paper
        conf_entry = next((e for e in res if "Just try, you can also succeed!" in e.title), None)
        self.assertIsNotNone(conf_entry)
        self.assertEqual(conf_entry.year, "2023")
        self.assertEqual(conf_entry.type, "conference")

    def test_chandan_semicolon_titles_and_preprints(self):
        """Verify clean title extraction before semicolon and preprint handling in CV_Chandan."""
        raw_pubs = {
            "journal_articles": [
                "12. Two-dimensional multigap superconductivity in bulk 2H-TaSeS; C. Patra, T. Agarwal, Ra- jeshwari R. Chaudhari, and R. P. Singh, Phys. Rev. B 106, 134515 (2022).",
                "Quasi-two-dimensional anisotropic superconductivity in Li-intercalated 2H-TaS ; T. Agarwal, 2 C. Patra, A. Kataria, Rajeswari R. Chowdhury, and R. P. Singh, Phys. Rev. B 107, 174509 (2023).",
                "25 3 hury,SamikDuttaGupta,ChandanPatra,AnshuKataria,ShunsukeFukami,andRaviPrakash Singh, Phys. Rev. Materials 6, 084408 (2022). Email: chandanpatra9696@gmail.com — Mobile: (+91)9609513143 Chandan Patra CV page 3 of 4",
            ],
            "preprints": [
                "SuperconductingPropertiesofTopologicalSemimetal1T-RhSeTe;C.Patra,T.Agarwal,Arushi, P. Manna, N. Bhatt, R. S. Singh, R. P. Singh, arXiv:2311.01019v1 (2023), under review in Phys- ical Review B."
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        titles = [e.title for e in res]

        # Semicolon title must not include authors or journal
        entry1 = next(e for e in res if "Two-dimensional multigap" in e.title)
        self.assertEqual(entry1.title, "Two-dimensional multigap superconductivity in bulk 2H-TaSeS")
        self.assertEqual(entry1.year, "2022")

        # Preprint title
        prep_entry = next(e for e in res if "SuperconductingProperties" in e.title)
        self.assertEqual(prep_entry.title, "SuperconductingPropertiesofTopologicalSemimetal1T-RhSeTe")
        self.assertEqual(prep_entry.year, "2023")

        # Page footer fragment must be filtered
        self.assertFalse(any("Chandan Patra CV page 3 of 4" in t for t in titles))

    def test_dibakar_title_first_and_page_vs_year(self):
        """Verify title-first isolation and page number distinction from publication year."""
        raw_pubs = {
            "journal_articles": [
                "1. Multi-stacked polarization insensitive broadband terahertz metamaterial, Bhagwat Singh Chouhan, Nityananda Acharyya, Anuraj Panwar, Dibakar Roy Chowdhury, and Gagan Kumar, IEEE Trans. Terahertz Sci. Technol. 14, 2024.",
                "Fano resonance-based CNT detection using THz MM, Shreeya Rane, Soumya Jyoti Mallick, Saloni Sharma, Nityananda Acharyya, Bipin Kumar Gupta, and Dibakar Roy Chowdhury, ACS Applied Optical Materials, 1 (12), 2004 (2023)",
            ],
            "conference_papers": [
                "Kumar, D., Rao, S. J. M., Kumar, G., & Roy Chowdhury, D. (2016, December). Modulating the Fundamental Resonances in Near Field Coupled Planar Terahertz Metamaterials. In International Conference on Fiber Optics and Photonics (pp. Tu4A-5). Optica Publishing Group."
            ]
        }
        res = self.normalizer.normalize(raw_pubs)

        # Title first: authors must not be part of the title
        entry1 = next(e for e in res if "Multi-stacked" in e.title)
        self.assertEqual(entry1.title, "Multi-stacked polarization insensitive broadband terahertz metamaterial")
        self.assertNotIn("Bhagwat Singh Chouhan", entry1.title)
        self.assertEqual(entry1.year, "2024")

        # Page number 2004 must not override publication year 2023
        entry2 = next(e for e in res if "Fano resonance" in e.title)
        self.assertEqual(entry2.year, "2023")

        # APA style in conference
        conf_entry = next(e for e in res if "Modulating the Fundamental Resonances" in e.title)
        self.assertEqual(conf_entry.year, "2016")
        self.assertEqual(conf_entry.type, "conference")

    def test_snehamoy_multi_pub_split_and_unspaced_titles(self):
        """Verify Snehamoy's concatenated publications are split and unspaced titles accepted."""
        text = (
            "2 S.Saha,Pramanik,Snehamoy,andN.Pradhan,“Analysisofthreedimensionalrayleigh-typewaves inalayeredstructure,”2023. "
            "3 S.Gupta,S.K.Das,andPramanik,Snehamoy,“Reflectionandtransmissionphenomenaofshwaves influidsaturatedporousmediumwithcorrugatedinterface,”MechanicsofAdvancedMaterialsand Structures,vol.29,no.26,pp.5122–5141,2022. "
            "Invited Talks/Presentation at National and International Conferences 2016 ] 11th International Symposium on Plasticity and Impact Mechanics"
        )
        raw_pubs = {"conference_papers": [text]}
        res = self.normalizer.normalize(raw_pubs)

        self.assertEqual(len(res), 2)
        titles = [e.title for e in res]
        self.assertTrue(any("Analysisofthreedimensionalrayleigh-typewaves" in t for t in titles))
        self.assertTrue(any("Reflectionandtransmissionphenomenaofshwaves" in t for t in titles))
        self.assertFalse(any("Invited Talks" in t for t in titles))

    def test_swapnil_shukla_authors_first_and_fragments(self):
        """Verify author list is not extracted as title and impact factor fragments are filtered."""
        raw_pubs = {
            "journal_articles": [
                "Nagarjuna Amarnath, Swapnil Shukla and Bimlesh Lochab, Harvesting the benefits of inherent reactive functionalities in fully bio-sourced isomeric benzoxazines, ACS Sus. Chem. Eng., 2018, 11, 15151-15161. (Impact Factor: 9.22)",
                "Arnab Ghosh#, Swapnil Shukla#, Monisha, Ajit Kumar, Bimlesh Lochab and Sagar Mitra, Sulfur Copolymer: A New Cathode Structure for Room-Temperature Sodium–Sulfur Batteries, ACS Ener. Lett., 2017, 2, 2478-2485. (Impact Factor: 23.99)",
                "(Impact Factor: 4.13)",
                "99) (Highlighted as the cover page of Macromolecular Chemistry and Physics)",
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        self.assertEqual(len(res), 2)

        titles = [e.title for e in res]
        self.assertIn("Harvesting the benefits of inherent reactive functionalities in fully bio-sourced isomeric benzoxazines", titles)
        self.assertIn("Sulfur Copolymer: A New Cathode Structure for Room-Temperature Sodium–Sulfur Batteries", titles)

        # Authors must not be the title
        self.assertNotIn("Swapnil Shukla and Bimlesh Lochab", titles)

    def test_rakesh_bhatnagar_attendance_filtered(self):
        """Verify pure conference attendances are completely filtered."""
        raw_pubs = {
            "conference_papers": [
                "❖ Attended the International Conference – PICOM 2024, International Conference on Changing Business Paradigms, Feb 23-24, 2024, Indore, Madhya Pradesh, India",
                "❖ Attended National Symposium held at S. K. Patel Institute of Management & Computer Studies, Gandhinagar from Aug 8-9, 2009.",
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        self.assertEqual(len(res), 0)

    def test_dr_cvr_summary_metrics_filtered(self):
        """Verify summary metrics table header is filtered."""
        raw_pubs = {
            "journal_articles": [
                "Total Publications Total Citations Citations per Paper Max Citation 99 819 8.326 42 h-index i10-index Cum. IF Average IF Max IF 17 29 204 2.069 9"
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        self.assertEqual(len(res), 0)

    def test_afzal_beg_venue_first_and_deduplication(self):
        """Verify Afzal Beg publications embedded in venue clauses are extracted and deduplicated."""
        raw_pubs = {
            "journal_articles": [
                "Paper Published at International Journal of Advanced Technology in Engineering and Science Study of Real-Time Circulation Activity Using Twitter Tweet Analytics Support NLP ISSN 2348-7550 |Vol. No. 09, Issue No. 12, December 2021"
            ],
            "books": [
                "Presented Paper in International Conference on Wireless, Mobile Network and Applications Tirumala Engineering College Jonnalagadda, Narasaraopet, Andhra Pradesh Study of Real-Time Circulation Activity Using Twitter Tweet Analytics Support NLP ISBN: 978-93-91535-02-5"
            ]
        }
        res = self.normalizer.normalize(raw_pubs)
        # Should be deduplicated into 1 entry
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].title, "Study of Real-Time Circulation Activity Using Twitter Tweet Analytics Support NLP")

    def test_publication_schema_and_no_leakage(self):
        """Verify that PublicationEntry schema contains strictly title, type, year, tier and never raw citations or venues."""
        entry = PublicationEntry(
            title="A Novel Method for Signal Processing",
            type="journal",
            year="2022",
            tier="Tier-2",
        )
        d = entry.to_dict()
        expected_keys = {"title", "type", "year", "tier"}
        self.assertEqual(set(d.keys()), expected_keys)
        self.assertNotIn("venue", d)
        self.assertNotIn("raw_citation", d)
        self.assertNotIn("doi", d)


if __name__ == "__main__":
    unittest.main()
