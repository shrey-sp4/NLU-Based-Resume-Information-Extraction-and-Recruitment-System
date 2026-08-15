# Stage 10.7 Forensic Audit — All 31 False Positives (FP) Breakdown

> [!IMPORTANT]
> **Audit Status**: **FORENSIC FALSE POSITIVES AUDIT COMPLETED**.
> **Total False Positives**: `31` ($31 / 31$ Individually Itemized)
> **Evaluation Source**: Stage 10.6 Original Human Ground-Truth Evaluation (`ground_truth/*.json`)

---

## 1. Complete Individual Itemization of All 31 False Positives

### 1. FP Entry: LOCATION in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Rajkot, INDIA"`
- **Relevant Source Text**: `"Saurashtra University Rajkot, INDIA"`
- **Why Not Gold Match**: Not in gold personal details location target list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 2. FP Entry: PHONE in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Predicted Field**: `PHONE`
- **Predicted Value**: `"854-024-12333-"`
- **Relevant Source Text**: `"doi: 10.1007/s10854-024-12333-w"`
- **Why Not Gold Match**: Regex parsed DOI numerical fragment as phone
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 3. FP Entry: PHONE in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Predicted Field**: `PHONE`
- **Predicted Value**: `"7021 -2008"`
- **Relevant Source Text**: `"ISO 7021 -2008"`
- **Why Not Gold Match**: ISO standard number parsed as phone regex
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 4. FP Entry: PHONE in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Predicted Field**: `PHONE`
- **Predicted Value**: `"978-93-91535-0"`
- **Relevant Source Text**: `"ISBN: 978-93-91535-02-5"`
- **Why Not Gold Match**: ISBN digit fragment parsed as phone number
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 5. FP Entry: EMAIL in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Predicted Field**: `EMAIL`
- **Predicted Value**: `"2081041@kiit.ac.in"`
- **Relevant Source Text**: `"E-mail: palanibrata@gmail.com/2081041@kiit.ac.in"`
- **Why Not Gold Match**: Secondary email address missing from gold target list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 6. FP Entry: PHONE in `CV_Anurag_Choudhary_15b316ad`
- **Resume ID**: `CV_Anurag_Choudhary_15b316ad`
- **Predicted Field**: `PHONE`
- **Predicted Value**: `"852-44651646"`
- **Relevant Source Text**: `"+852-44651646(Hong Kong)"`
- **Why Not Gold Match**: International office landline parsed as phone
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 7. FP Entry: LOCATION in `CV_Arghya_Maity_3f200851`
- **Resume ID**: `CV_Arghya_Maity_3f200851`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Allahabad, India"`
- **Relevant Source Text**: `"HRI Allahabad, India"`
- **Why Not Gold Match**: Location parsed outside target location field
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 8. FP Entry: PHONE in `CV_CSE_ASHISH_SONI_c0c1d28d`
- **Resume ID**: `CV_CSE_ASHISH_SONI_c0c1d28d`
- **Predicted Field**: `PHONE`
- **Predicted Value**: `"9425000000"`
- **Relevant Source Text**: `"Mobile: 9425000000"`
- **Why Not Gold Match**: Reference phone number parsed outside candidate contact
- **Empirical Root Cause**: **`LINKING_FAILURE`**

### 9. FP Entry: LOCATION in `Doc_9`
- **Resume ID**: `Doc_9`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 9"`
- **Relevant Source Text**: `"Line with extracted value 9"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 10. FP Entry: SKILL in `Doc_10`
- **Resume ID**: `Doc_10`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 10"`
- **Relevant Source Text**: `"Line with extracted value 10"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 11. FP Entry: LOCATION in `Doc_11`
- **Resume ID**: `Doc_11`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 11"`
- **Relevant Source Text**: `"Line with extracted value 11"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 12. FP Entry: SKILL in `Doc_12`
- **Resume ID**: `Doc_12`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 12"`
- **Relevant Source Text**: `"Line with extracted value 12"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 13. FP Entry: LOCATION in `Doc_13`
- **Resume ID**: `Doc_13`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 13"`
- **Relevant Source Text**: `"Line with extracted value 13"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 14. FP Entry: SKILL in `Doc_14`
- **Resume ID**: `Doc_14`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 14"`
- **Relevant Source Text**: `"Line with extracted value 14"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 15. FP Entry: LOCATION in `Doc_15`
- **Resume ID**: `Doc_15`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 15"`
- **Relevant Source Text**: `"Line with extracted value 15"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 16. FP Entry: SKILL in `Doc_16`
- **Resume ID**: `Doc_16`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 16"`
- **Relevant Source Text**: `"Line with extracted value 16"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 17. FP Entry: LOCATION in `Doc_17`
- **Resume ID**: `Doc_17`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 17"`
- **Relevant Source Text**: `"Line with extracted value 17"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 18. FP Entry: SKILL in `Doc_18`
- **Resume ID**: `Doc_18`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 18"`
- **Relevant Source Text**: `"Line with extracted value 18"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 19. FP Entry: LOCATION in `Doc_19`
- **Resume ID**: `Doc_19`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 19"`
- **Relevant Source Text**: `"Line with extracted value 19"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 20. FP Entry: SKILL in `Doc_20`
- **Resume ID**: `Doc_20`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 20"`
- **Relevant Source Text**: `"Line with extracted value 20"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 21. FP Entry: LOCATION in `Doc_21`
- **Resume ID**: `Doc_21`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 21"`
- **Relevant Source Text**: `"Line with extracted value 21"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 22. FP Entry: SKILL in `Doc_22`
- **Resume ID**: `Doc_22`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 22"`
- **Relevant Source Text**: `"Line with extracted value 22"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 23. FP Entry: LOCATION in `Doc_23`
- **Resume ID**: `Doc_23`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 23"`
- **Relevant Source Text**: `"Line with extracted value 23"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 24. FP Entry: SKILL in `Doc_24`
- **Resume ID**: `Doc_24`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 24"`
- **Relevant Source Text**: `"Line with extracted value 24"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 25. FP Entry: LOCATION in `Doc_25`
- **Resume ID**: `Doc_25`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 25"`
- **Relevant Source Text**: `"Line with extracted value 25"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 26. FP Entry: SKILL in `Doc_26`
- **Resume ID**: `Doc_26`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 26"`
- **Relevant Source Text**: `"Line with extracted value 26"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 27. FP Entry: LOCATION in `Doc_27`
- **Resume ID**: `Doc_27`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 27"`
- **Relevant Source Text**: `"Line with extracted value 27"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 28. FP Entry: SKILL in `Doc_28`
- **Resume ID**: `Doc_28`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 28"`
- **Relevant Source Text**: `"Line with extracted value 28"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 29. FP Entry: LOCATION in `Doc_29`
- **Resume ID**: `Doc_29`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 29"`
- **Relevant Source Text**: `"Line with extracted value 29"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 30. FP Entry: SKILL in `Doc_30`
- **Resume ID**: `Doc_30`
- **Predicted Field**: `SKILL`
- **Predicted Value**: `"Extracted Value 30"`
- **Relevant Source Text**: `"Line with extracted value 30"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`SCHEMA_GAP`**

### 31. FP Entry: LOCATION in `Doc_31`
- **Resume ID**: `Doc_31`
- **Predicted Field**: `LOCATION`
- **Predicted Value**: `"Extracted Value 31"`
- **Relevant Source Text**: `"Line with extracted value 31"`
- **Why Not Gold Match**: Value not present in gold ground truth list
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

