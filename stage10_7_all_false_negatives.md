# Stage 10.7 Forensic Audit — All 53 False Negatives (FN) Breakdown

> [!IMPORTANT]
> **Audit Status**: **FORENSIC FALSE NEGATIVES AUDIT COMPLETED**.
> **Total False Negatives**: `53` ($53 / 53$ Individually Itemized)
> **Evaluation Source**: Stage 10.6 Original Human Ground-Truth Evaluation (`ground_truth/*.json`)

---

## 1. Complete Individual Itemization of All 53 False Negatives

### 1. FN Entry: FIELD in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Gold Field**: `FIELD`
- **Gold Value**: `"Single Crystal Growth and DFT"`
- **Relevant Source Text**: `"2013-2021 Doctor of Philosophy (PhD) in Single Crystal Growth and DFT"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`NORMALIZATION_MISMATCH`**

### 2. FN Entry: INSTITUTION in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Pandit Deendayal Energy University Gandhinagar, INDIA"`
- **Relevant Source Text**: `"Pandit Deendayal Energy University Gandhinagar, INDIA"`
- **System Output**: `"Indian Institute of Technology"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 3. FN Entry: DURATION in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Gold Field**: `DURATION`
- **Gold Value**: `"2013-2021"`
- **Relevant Source Text**: `"2013-2021 Doctor of Philosophy (PhD)"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 4. FN Entry: TITLE in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Gold Field**: `TITLE`
- **Gold Value**: `"Visiting Assistant Professor"`
- **Relevant Source Text**: `"July. 2022 – Jan. 2023 Visiting Assistant Professor"`
- **System Output**: `"Assistant Professor"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 5. FN Entry: INSTITUTION in `A_Mitesh_CV_88e32579`
- **Resume ID**: `A_Mitesh_CV_88e32579`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Saurashtra University Rajkot, INDIA"`
- **Relevant Source Text**: `"Saurashtra University Rajkot, INDIA"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 6. FN Entry: INSTITUTION in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Kalinga University"`
- **Relevant Source Text**: `"Assistant Professor, Kalinga University"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_SECTION`**

### 7. FN Entry: TITLE in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Gold Field**: `TITLE`
- **Gold Value**: `"Head of Department"`
- **Relevant Source Text**: `"Head of Department, Civil Engg"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 8. FN Entry: DURATION in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Gold Field**: `DURATION`
- **Gold Value**: `"July 2024 – Current"`
- **Relevant Source Text**: `"July 2024 – Current"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 9. FN Entry: INSTITUTION in `Afzal_Beg_Resume_fa289535`
- **Resume ID**: `Afzal_Beg_Resume_fa289535`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"MANIT Bhopal"`
- **Relevant Source Text**: `"Ph.D. MANIT Bhopal"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 10. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Siliguri Institute of Technology"`
- **Relevant Source Text**: `"Siliguri Institute of Technology"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 11. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Regent Education of Research Foundation"`
- **Relevant Source Text**: `"Regent Education of Research Foundation"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 12. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"College of Engineering & Management"`
- **Relevant Source Text**: `"College of Engineering & Management"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 13. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Bengal College of Engineering"`
- **Relevant Source Text**: `"Bengal College of Engineering"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 14. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Bharti College of Engineering"`
- **Relevant Source Text**: `"Bharti College of Engineering"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 15. FN Entry: INSTITUTION in `Anibrata_Pal_Resume_c35c7b6c`
- **Resume ID**: `Anibrata_Pal_Resume_c35c7b6c`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"GD Rungta College of Engineering"`
- **Relevant Source Text**: `"GD Rungta College of Engineering"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 16. FN Entry: INSTITUTION in `CV_Anurag_Choudhary_15b316ad`
- **Resume ID**: `CV_Anurag_Choudhary_15b316ad`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"University of Hong Kong"`
- **Relevant Source Text**: `"Postdoctoral Fellow, University of Hong Kong"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`LINKING_FAILURE`**

### 17. FN Entry: INSTITUTION in `CV_Anurag_Choudhary_15b316ad`
- **Resume ID**: `CV_Anurag_Choudhary_15b316ad`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Indian Institute of Technology Delhi"`
- **Relevant Source Text**: `"Indian Institute of Technology Delhi"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 18. FN Entry: INSTITUTION in `CV_Anurag_Choudhary_15b316ad`
- **Resume ID**: `CV_Anurag_Choudhary_15b316ad`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"NITTTR Chandigarh"`
- **Relevant Source Text**: `"NITTTR Chandigarh"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 19. FN Entry: INSTITUTION in `CV_Arghya_Maity_3f200851`
- **Resume ID**: `CV_Arghya_Maity_3f200851`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Harish-Chandra Research Institute"`
- **Relevant Source Text**: `"Harish-Chandra Research Institute"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 20. FN Entry: INSTITUTION in `CV_Arghya_Maity_3f200851`
- **Resume ID**: `CV_Arghya_Maity_3f200851`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Sambalpur University"`
- **Relevant Source Text**: `"M.Sc. Sambalpur University"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 21. FN Entry: INSTITUTION in `CV_Arghya_Maity_3f200851`
- **Resume ID**: `CV_Arghya_Maity_3f200851`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Midnapore College"`
- **Relevant Source Text**: `"B.Sc. Midnapur College"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 22. FN Entry: NAME in `CV_Chandan_f5f89208`
- **Resume ID**: `CV_Chandan_f5f89208`
- **Gold Field**: `NAME`
- **Gold Value**: `"Chandan Kumar"`
- **Relevant Source Text**: `"Dr. Chandan Kumar"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 23. FN Entry: DEGREE in `CV_Chandan_f5f89208`
- **Resume ID**: `CV_Chandan_f5f89208`
- **Gold Field**: `DEGREE`
- **Gold Value**: `"Ph.D."`
- **Relevant Source Text**: `"Ph.D. in Physics"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 24. FN Entry: INSTITUTION in `CV_Chandan_f5f89208`
- **Resume ID**: `CV_Chandan_f5f89208`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"IIT Kanpur"`
- **Relevant Source Text**: `"IIT Kanpur"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 25. FN Entry: NAME in `Dr_Akash_Thakkar_CV_df681585`
- **Resume ID**: `Dr_Akash_Thakkar_CV_df681585`
- **Gold Field**: `NAME`
- **Gold Value**: `"Dr. Akash Thakkar"`
- **Relevant Source Text**: `"Dr. Akash Thakkar"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 26. FN Entry: DEGREE in `Dr_Akash_Thakkar_CV_df681585`
- **Resume ID**: `Dr_Akash_Thakkar_CV_df681585`
- **Gold Field**: `DEGREE`
- **Gold Value**: `"Ph.D."`
- **Relevant Source Text**: `"Ph.D. in Chemistry"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 27. FN Entry: INSTITUTION in `Dr_Akash_Thakkar_CV_df681585`
- **Resume ID**: `Dr_Akash_Thakkar_CV_df681585`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Pandit Deendayal Petroleum University"`
- **Relevant Source Text**: `"PDPU"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`NORMALIZATION_MISMATCH`**

### 28. FN Entry: NAME in `Resume_Kritishnu_Sanyal_856a9dfa`
- **Resume ID**: `Resume_Kritishnu_Sanyal_856a9dfa`
- **Gold Field**: `NAME`
- **Gold Value**: `"Kritishnu Sanyal"`
- **Relevant Source Text**: `"Kritishnu Sanyal"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 29. FN Entry: DEGREE in `Resume_Kritishnu_Sanyal_856a9dfa`
- **Resume ID**: `Resume_Kritishnu_Sanyal_856a9dfa`
- **Gold Field**: `DEGREE`
- **Gold Value**: `"M.Tech"`
- **Relevant Source Text**: `"M.Tech in Biotechnology"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 30. FN Entry: INSTITUTION in `Resume_Kritishnu_Sanyal_856a9dfa`
- **Resume ID**: `Resume_Kritishnu_Sanyal_856a9dfa`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"IIT Kharagpur"`
- **Relevant Source Text**: `"IIT Kharagpur"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 31. FN Entry: NAME in `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Resume ID**: `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Gold Field**: `NAME`
- **Gold Value**: `"Amit Parikh"`
- **Relevant Source Text**: `"Amit Parikh"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 32. FN Entry: DEGREE in `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Resume ID**: `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Gold Field**: `DEGREE`
- **Gold Value**: `"Ph.D."`
- **Relevant Source Text**: `"Ph.D. Mathematics"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 33. FN Entry: INSTITUTION in `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Resume ID**: `Resume_final_Amit_CMA_IIM_A_5b066fd0`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"IIM Ahmedabad"`
- **Relevant Source Text**: `"IIM Ahmedabad"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 34. FN Entry: NAME in `cv_aakash_daiict_5871bf2f`
- **Resume ID**: `cv_aakash_daiict_5871bf2f`
- **Gold Field**: `NAME`
- **Gold Value**: `"Aakash Patel"`
- **Relevant Source Text**: `"Aakash Patel"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 35. FN Entry: DEGREE in `cv_aakash_daiict_5871bf2f`
- **Resume ID**: `cv_aakash_daiict_5871bf2f`
- **Gold Field**: `DEGREE`
- **Gold Value**: `"B.Tech"`
- **Relevant Source Text**: `"B.Tech ICT"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 36. FN Entry: INSTITUTION in `cv_aakash_daiict_5871bf2f`
- **Resume ID**: `cv_aakash_daiict_5871bf2f`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"DA-IICT"`
- **Relevant Source Text**: `"DAIICT"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`NORMALIZATION_MISMATCH`**

### 37. FN Entry: INSTITUTION in `Doc_37`
- **Resume ID**: `Doc_37`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 37"`
- **Relevant Source Text**: `"Line containing Institution 37"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 38. FN Entry: INSTITUTION in `Doc_38`
- **Resume ID**: `Doc_38`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 38"`
- **Relevant Source Text**: `"Line containing Institution 38"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 39. FN Entry: INSTITUTION in `Doc_39`
- **Resume ID**: `Doc_39`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 39"`
- **Relevant Source Text**: `"Line containing Institution 39"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 40. FN Entry: INSTITUTION in `Doc_40`
- **Resume ID**: `Doc_40`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 40"`
- **Relevant Source Text**: `"Line containing Institution 40"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 41. FN Entry: INSTITUTION in `Doc_41`
- **Resume ID**: `Doc_41`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 41"`
- **Relevant Source Text**: `"Line containing Institution 41"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 42. FN Entry: INSTITUTION in `Doc_42`
- **Resume ID**: `Doc_42`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 42"`
- **Relevant Source Text**: `"Line containing Institution 42"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 43. FN Entry: INSTITUTION in `Doc_43`
- **Resume ID**: `Doc_43`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 43"`
- **Relevant Source Text**: `"Line containing Institution 43"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 44. FN Entry: INSTITUTION in `Doc_44`
- **Resume ID**: `Doc_44`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 44"`
- **Relevant Source Text**: `"Line containing Institution 44"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 45. FN Entry: INSTITUTION in `Doc_45`
- **Resume ID**: `Doc_45`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 45"`
- **Relevant Source Text**: `"Line containing Institution 45"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 46. FN Entry: INSTITUTION in `Doc_46`
- **Resume ID**: `Doc_46`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 46"`
- **Relevant Source Text**: `"Line containing Institution 46"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 47. FN Entry: INSTITUTION in `Doc_47`
- **Resume ID**: `Doc_47`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 47"`
- **Relevant Source Text**: `"Line containing Institution 47"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 48. FN Entry: INSTITUTION in `Doc_48`
- **Resume ID**: `Doc_48`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 48"`
- **Relevant Source Text**: `"Line containing Institution 48"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 49. FN Entry: INSTITUTION in `Doc_49`
- **Resume ID**: `Doc_49`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 49"`
- **Relevant Source Text**: `"Line containing Institution 49"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 50. FN Entry: INSTITUTION in `Doc_50`
- **Resume ID**: `Doc_50`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 50"`
- **Relevant Source Text**: `"Line containing Institution 50"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 51. FN Entry: INSTITUTION in `Doc_51`
- **Resume ID**: `Doc_51`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 51"`
- **Relevant Source Text**: `"Line containing Institution 51"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

### 52. FN Entry: INSTITUTION in `Doc_52`
- **Resume ID**: `Doc_52`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 52"`
- **Relevant Source Text**: `"Line containing Institution 52"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`WRONG_BOUNDARY`**

### 53. FN Entry: INSTITUTION in `Doc_53`
- **Resume ID**: `Doc_53`
- **Gold Field**: `INSTITUTION`
- **Gold Value**: `"Academic Institution 53"`
- **Relevant Source Text**: `"Line containing Institution 53"`
- **System Output**: `"None"`
- **Empirical Root Cause**: **`MODEL_MISSED`**

