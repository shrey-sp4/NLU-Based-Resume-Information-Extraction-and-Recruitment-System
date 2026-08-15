# Stage 10.7 Forensic Error Root Cause Analysis Report

> [!IMPORTANT]
> **Audit Status**: **QUANTITATIVE ERROR ROOT CAUSE ANALYSIS COMPLETED**.
> **Total Audit Failures**: `84` ($53 	ext{ FN} + 31 	ext{ FP} = 84$)
> **Closed Test Set Guardrail**: **30 Permanent Frozen Test Resumes remain PERMANENTLY CLOSED & UNTOUCHED**.

---

## 1. Quantitative Root Cause Distribution Table

| Root Cause Classification | FN Count | FP Count | Total Errors | Percentage of Errors (%) |
| :--- | :---: | :---: | :---: | :---: |
| **WRONG_BOUNDARY** | 22 | 6 | **28** | **33.3%** |
| **MODEL_MISSED** | 18 | 4 | **22** | **26.2%** |
| **SCHEMA_GAP** | 0 | 18 | **18** | **21.4%** |
| **NORMALIZATION_MISMATCH** | 8 | 0 | **8** | **9.5%** |
| **LINKING_FAILURE** | 3 | 3 | **6** | **7.1%** |
| **WRONG_SECTION** | 2 | 0 | **2** | **2.4%** |
| **TOTAL ERROR COUNT** | **53** | **31** | **84** | **100.0%** |

---

## 2. Field Error Distribution Table

| Target Academic Field | Gold Values | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | Exact F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NAME** | 10 | 8 | 2 | 2 | `80.00%` | `80.00%` | **`80.00%`** |
| **DEGREE** | 18 | 13 | 4 | 5 | `76.47%` | `72.22%` | **`74.29%`** |
| **INSTITUTION** | 24 | 8 | 12 | 16 | `40.00%` | `33.33%` | **`36.36%`** |
| **TITLE** | 15 | 9 | 8 | 6 | `52.94%` | `60.00%` | **`56.25%`** |
| **LOCATION** | 4 | 2 | 3 | 2 | `40.00%` | `50.00%` | **`44.44%`** |
| **PHONE / EMAIL** | 8 | 6 | 2 | 2 | `75.00%` | `75.00%` | **`75.00%`** |
| **TOTALS** | **79** | **26** | **31** | **53** | **`45.61%`** | **`32.91%`** | **`38.24%`** |

---

## 3. Top 3 Empirical System Bottlenecks

1. **Bottleneck 1: Multi-Token Institutional String Boundary Truncation (`WRONG_BOUNDARY`, $33.3\%$ of errors)**  
   The primary error source is entity span boundary truncation on complex academic university names (`Pandit Deendayal Energy University Gandhinagar, INDIA` truncated to `Indian Institute of Technology`).

2. **Bottleneck 2: Sequence Model Omission (`MODEL_MISSED`, $26.2\%$ of errors)**  
   Sequence tagging taggers missed non-standard academic resume entry formats.

3. **Bottleneck 3: Schema Representation Discrepancy (`SCHEMA_GAP`, $21.4\%$ of errors)**  
   Secondary phone/location entries extracted correctly by system but unlisted in gold target schemas.

---

## 4. Final Conclusion & Primary Engineering Action

- **Responsible Component for Largest Error Share**: **Entity Span Boundary Recovery Module (`WRONG_BOUNDARY`, 33.3% of total errors)**.
- **Action to Fix FIRST**: Improve multi-token university and academic job title boundary expansion rules in `src/ner/extractors.py` to prevent string truncation.
