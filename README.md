# NLU-Based Resume Information Extraction and Recruitment System

An NLU-driven end-to-end resume information extraction, sectioning, structured entity parsing, and recruitment recommendation system.

---

## 📊 Final 25-Field Pipeline Accuracy Metrics

The extraction pipeline is evaluated end-to-end against 10 ground-truth academic resumes across 25 fields. Below is the strict accuracy table produced by `scratch/evaluate_pipeline.py`.

| FIELD NAME | PRECISION | RECALL | F1 SCORE |
| :--- | :---: | :---: | :---: |
| `certifications` | 53.16% | 65.08% | **56.33%** |
| `education_cgpa` | 100.00% | 55.00% | **66.56%** |
| `education_degree` | 69.42% | 32.33% | **39.68%** |
| `education_graduation_year` | 100.00% | 55.29% | **65.95%** |
| `education_institution` | 53.33% | 27.41% | **33.69%** |
| `experience_dates` | 65.74% | 45.83% | **47.96%** |
| `experience_institution` | 81.48% | 48.15% | **55.06%** |
| `experience_title` | 82.22% | 48.81% | **55.76%** |
| `personal_email` | 77.78% | 77.78% | **77.78%** |
| `personal_name` | 77.78% | 77.78% | **77.78%** |
| `personal_phone` | 55.56% | 55.56% | **55.56%** |
| `projects` | 55.56% | 51.48% | **53.31%** |
| `publications_book_chapters` | 74.69% | 70.79% | **72.12%** |
| `publications_books` | 77.78% | 77.78% | **77.78%** |
| `publications_communications` | 88.89% | 88.89% | **88.89%** |
| `publications_conference_papers` | 48.66% | 51.46% | **49.20%** |
| `publications_conference_proceedings` | 86.70% | 88.41% | **87.43%** |
| `publications_journal_articles` | 55.24% | 73.09% | **58.96%** |
| `publications_preprints` | 63.43% | 61.28% | **62.18%** |
| `publications_technical_reports` | 88.89% | 88.89% | **88.89%** |
| `references` | 71.99% | 63.66% | **67.39%** |
| `research_interests` | 70.53% | 100.00% | **76.71%** |
| `responsibilities` | 72.01% | 84.77% | **74.31%** |
| `skills` | 73.66% | 97.79% | **78.64%** |
| `summary` | 58.41% | 66.67% | **61.51%** |
| **AVERAGE MACRO FIELD F1 (25 FIELDS)** | | | **65.18%** |

---

## 🔍 Known Pipeline Limitations

1. **`personal_phone` (55.56% F1)**: Phone regex extracts bare 10-digit mobile numbers; landline and international extensions may be truncated.
2. **`education_institution` (33.69% F1) & `experience_institution` (55.06% F1)**: Multi-word university names split across line breaks or containing lowercase prepositions (e.g. `sanchar Vishwavidhyalay`) can be truncated.
3. **`publications_conference_papers` (49.20% F1)**: Short workshop and conference acronyms without explicit `"Conference"` or `"Symposium"` keywords default to `"journal_articles"`.

---

## 🛠️ Reproduction & Evaluation

To re-run the consolidated 25-field end-to-end evaluation:

```bash
python scratch/evaluate_pipeline.py
```

This generates:
- `output/evaluation/section_metrics.csv`
- `output/evaluation/overall_metrics.csv`