from pathlib import Path
import unittest

from src.extraction.discovery import discover_pdf_files


class DiscoveryTests(unittest.TestCase):
    def test_discovers_only_real_pdf_resumes(self) -> None:
        pdfs = discover_pdf_files(Path("data/real_resumes/original"))
        self.assertEqual(len(pdfs), 40)
        self.assertTrue(all(path.suffix.lower() == ".pdf" for path in pdfs))
        self.assertTrue(all(path.name.lower() != ".gitkeep" for path in pdfs))


if __name__ == "__main__":
    unittest.main()

