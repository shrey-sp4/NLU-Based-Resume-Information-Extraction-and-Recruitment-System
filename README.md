# NLU-Based Resume Information Extraction and Recruitment System

An NLU-driven end-to-end resume information extraction, sectioning, structured entity parsing, and recruitment recommendation system.

---

## 📊 Final 25-Field Pipeline Accuracy Metrics

The extraction pipeline is evaluated end-to-end against 10 ground-truth academic resumes across 25 fields. Below is the strict accuracy table produced by `scratch/evaluate_pipeline.py`.

| FIELD NAME | PRECISION | RECALL | F1 SCORE |
| :--- | :---: | :---: | :---: |
| `certifications` | 47.84% | 58.57% | 50.70% |
| `education_cgpa` | 90.00% | 68.83% | **74.56%** |
| `education_degree` | 62.29% | 55.29% | **55.48%** |
| `education_graduation_year` | 94.67% | 69.71% | **78.30%** |
| `education_institution` | 60.83% | 36.26% | **43.01%** |
| `experience_dates` | 73.00% | 56.67% | **61.58%** |
| `experience_institution` | 53.17% | 35.00% | **40.58%** |
| `experience_title` | 81.00% | 66.25% | **71.03%** |
| `personal_email` | 80.00% | 80.00% | **80.00%** |
| `personal_name` | 80.00% | 80.00% | **80.00%** |
| `personal_phone` | 30.00% | 30.00% | **30.00%** |
| `projects` | 55.83% | 55.70% | **55.16%** |
| `publications_book_chapters` | 77.22% | 73.71% | **74.91%** |
| `publications_books` | 80.00% | 80.00% | **80.00%** |
| `publications_communications` | 80.00% | 80.00% | **80.00%** |
| `publications_conference_papers` | 43.79% | 46.32% | **44.28%** |
| `publications_conference_proceedings` | 88.03% | 89.57% | **88.68%** |
| `publications_journal_articles` | 57.07% | 73.36% | **60.52%** |
| `publications_preprints` | 67.08% | 65.15% | **65.96%** |
| `publications_technical_reports` | 90.00% | 90.00% | **90.00%** |
| `references` | 74.15% | 65.35% | **69.31%** |
| `research_interests` | 73.47% | 100.00% | **79.04%** |
| `responsibilities` | 74.81% | 86.29% | **76.88%** |
| `skills` | 76.30% | 95.79% | **79.53%** |
| `summary` | 62.57% | 70.00% | **65.36%** |
| **AVERAGE MACRO FIELD F1 (25 FIELDS)** | | | **66.99%** |

---

## 🔍 Known Pipeline Limitations

1. **`personal_phone` (30.00% F1)**: International phone formats (e.g. `+91-9876543210` vs `(02692) 230101`) have format variations that standard 10-digit normalizers partially miss.
2. **`education_institution` (43.01% F1) & `experience_institution` (40.58% F1)**: Multi-word university names split across PDF text lines or complex multi-campus names (e.g., `Department of Applied Science, School of Emerging Science, Gujarat University`) are sometimes truncated at line breaks.
3. **`publications_conference_papers` (44.28% F1)**: Short workshop and conference acronyms without explicit `"Conference"` or `"Symposium"` keywords default to the `"journal_articles"` classification bucket.

---

## 🛠️ Reproduction & Evaluation

To re-run the consolidated 25-field end-to-end evaluation:

```bash
python scratch/evaluate_pipeline.py
```

This generates:
- `output/evaluation/section_metrics.csv`
- `output/evaluation/overall_metrics.csv`