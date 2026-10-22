# Resume Shortlisting System

## 1. Objective

The Resume Shortlisting System is a downstream recruitment and decision-support module built on top of the existing Natural Language Understanding (NLU) resume information-extraction pipeline in this repository. 

The existing extraction pipeline remains completely unchanged and operates independently.

### Architecture Flow:
```
Resume Document
       ↓
Existing Extraction Pipeline
       ↓
output/predictions/*.json
       ↓
Candidate Normalization (Education, Experience, Publications)
       ↓
Tier Classification (University & Publication Venues)
       ↓
Recruiter Requirements Evaluation
       ↓
Hard Gates & Soft Gates Evaluation
       ↓
Multi-Criteria Scoring
       ↓
Final Decision (SHORTLISTED / REVIEW / REJECTED)
```

---

## 2. Current Input

The system consumes pre-extracted resume predictions stored in:
```
output/predictions/*.json
```
These prediction JSON files serve as read-only, source-of-truth inputs. They are never modified, edited, or overwritten by the shortlisting system.

---

## 3. What Has Been Completed

### Extraction Evaluation
- Thoroughly audited and evaluated the output of the existing extraction pipeline against ground truth data.
- Analyzed extraction performance across all primary recruitment entities: Education, Experience, and Publications.
- Used the `experiment/robust-extraction-pipeline` branch as the stable baseline and sole source of upstream candidate extraction data.

### Shortlisting Architecture
Built a modular, decoupled Python package in [`shortlisting/`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting) structured as follows:
- **`models/`**: Domain schemas for normalized candidates ([`candidate.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/models/candidate.py)), recruiter requirements ([`requirements.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/models/requirements.py)), and decision outcomes ([`evaluation.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/models/evaluation.py)).
- **`normalization/`**: Conservative cleaning modules for education, experience, and publication records.
- **`llm/`**: Modular interfaces and fallback taxonomies for institutional tiering and publication tiering.
- **`engine/`**: Gate evaluation ([`matcher.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/engine/matcher.py)), weighted composite scoring ([`scorer.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/engine/scorer.py)), and threshold decision-making ([`decision.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/engine/decision.py)).
- **`config/`**: Externalized scoring weights ([`scoring_config.json`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/config/scoring_config.json)), university taxonomy ([`university_taxonomy.json`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/config/university_taxonomy.json)), and publication venue taxonomy ([`publication_taxonomy.json`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/config/publication_taxonomy.json)).
- **`reporting/`**: Audit trail and explainability generators ([`explainability.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/reporting/explainability.py)).
- **`ui/`**: Interactive Streamlit dashboard application ([`shortlisting_app.py`](file:///Users/subratotapaswi/Documents/NLU_based_extraction_shortlisting/shortlisting/ui/shortlisting_app.py)).

### Candidate Normalization

#### Education:
- Normalizes degree name, stream (where explicitly available), institution name, and assigned university tier.
- Conservative noise filtering: eliminates resume table headers, standalone thesis topics, advisor lines, and secondary-school-only records.
- Prevents over-filtering: preserves valid higher-education degrees even when secondary-school strings or course names appear elsewhere in multiline raw text.
- Replaces brittle word-count thresholds with clean prefix/suffix stripping to preserve legitimate short institution names.

#### Experience:
- Normalizes job title, employer/institution, employment dates, professional categorization (academic vs. industry vs. other), and duration in years.
- Resilient date parsing: supports various date-range formats (`to`, `till`, en-dash, em-dash, month/year ranges, and `Present`).
- Fallback parsing: inspects `raw_text` for explicit date endpoints only when structured dates contain incomplete single-year fragments.

#### Publications:
- Normalizes publication title, venue type (journal vs. conference vs. other), publication year, and assigned tier.
- Eliminates noise headings, author list dumps, and duplicate citations.

> **STRICT NO-FABRICATION RULE**:
> Normalization strictly adheres to a zero-fabrication constraint. Values must be directly traceable to facts present in the source prediction JSON. Missing degrees, dates, streams, or institutions remain explicitly empty (`""`, `None`, or `Unknown`). The system never guesses or synthesizes data.

### Recruiter Requirements
The engine provides recruiter configurable requirement profiles:
- **Mandatory Hard Gates**: Strict binary requirements (e.g., must possess Ph.D, minimum publication count). Any failure immediately marks the candidate as `REJECTED`.
- **Soft/Scored Requirements**: Flexible preferences evaluated during scoring (e.g., preferred university tiers, academic experience duration, specific role alignment, recent publication activity).
- **Configurable Thresholds**: Adjustable shortlist and review score cutoffs.
- **Configurable Weights**: Fully custom component weights across dimensions.

The current baseline profile models an **Assistant Professor / Academic Researcher** position.

### Matching and Scoring
Current configured overall component weights:
- **Education**: 35% (0.35)
- **Experience**: 35% (0.35)
- **Publications**: 30% (0.30)

Current decision thresholds:
- **SHORTLISTED**: Overall Score $\ge$ 75.0 (with all hard gates met)
- **REVIEW**: Overall Score $\ge$ 60.0 and $<$ 75.0 (with all hard gates met)
- **REJECTED**: Overall Score $<$ 60.0 OR failure of any mandatory hard gate

Component considerations:
- **Education**: Degree fulfillment and university tier quality (aggregated by highest degree or weighted degree levels).
- **Experience**: Total and academic duration fulfillment balanced with target relevant-role alignment.
- **Publications**: Publication volume, journal/conference breakdown, venue tier quality, and publication recency window.

---

## 4. Example Current Output

The shortlisting system evaluates individual candidates end-to-end with complete explainability. For example, for candidate **Priya Ranjan Sahoo** (`Priya_Ranjan_Sahoo_CV.json`), the system:
1. Verifies the mandatory Ph.D hard gate $\rightarrow$ **PASS** (Ph.D from University of Delhi).
2. Verifies the mandatory publication count $\rightarrow$ **PASS** (15 publications $\ge$ 2 minimum).
3. Evaluates university quality $\rightarrow$ Tier-2 (Score: 85.0).
4. Evaluates verified academic experience $\rightarrow$ 4.8 years as Postdoctoral Fellow (Score: 70.0).
5. Evaluates publication record $\rightarrow$ 11 journals, 4 conferences, 6 recent papers (Score: 87.1).
6. Computes composite score:
   $$\text{Overall} = (0.35 \times 85.0) + (0.35 \times 70.0) + (0.30 \times 87.1) = \mathbf{80.38}$$
7. Outputs final decision: **SHORTLISTED** ($\ge 75.0$).

The complete pipeline has been executed across all 40 prediction files in the dataset, generating candidate-level evaluation records and summary decision metrics.

*Note: The current 40-candidate results serve as a working architectural milestone and baseline validation; they are not final production outputs, as full education and publication normalization refinement is ongoing.*

---

## 5. LLM Integration & Classification Status

LLM integration for university-tier and publication-tier classification is implemented with **Google Gemini (`gemini-1.5-flash`)** as the primary provider:
- **Standard Library Transport**: Uses Python's built-in `urllib.request` for direct, dependency-free API calls.
- **University Classification**: Evaluates institutions into Tier-1 / Tier-2 / Tier-3 / Unknown based on configurable taxonomies. Prompt is strictly decoupled from candidate degrees to prevent bias.
- **Publication Classification**: Evaluates citations into Tier-1 / Tier-2 / Tier-3 / Unranked based on explicit venue evidence. Unverified venues safely default to `Unranked`.
- **Offline Heuristic & Error Fallback**: Automatically falls back to deterministic rule-based evaluation when API credentials are absent or network errors occur, transparently attributing the source (`gemini`, `offline_fallback`, or `api_error_fallback`).

---

## 6. Project Status & Next Steps

1. **Stage 1 (Education Normalization)**: Complete & validated with 8 unit tests.
2. **Stage 2 (Publication Normalization)**: Complete & validated with 10 unit tests.
3. **Stage 3 (Gemini LLM Integration)**: Complete & verified with 8 mocked unit tests covering offline mode, successful generation, error handling, prompt independence, and schema preservation.
4. **Candidate Name Normalization**: Complete & validated with 4 regression tests covering heading rejection and prefix stripping (total 30 unit tests passing).
5. **Candidate Decision Counts Across 40 Resumes** (Decision counts under default requirements, not accuracy measurements):
   - Baseline Predictions: 27 Shortlisted, 10 Review, 3 Rejected.
   - Latest Predictions (robust-extraction-pipeline): 28 Shortlisted, 8 Review, 4 Rejected.
6. **Next Steps for Production Readiness**:
   - Optional live API key execution in production deployment environments.
   - Additional recruiter UI custom filtering controls.
   - Batch report generation (PDF / CSV) for faculty selection committees.

## 7. Design Principles

- **Separation of Concerns**: The existing extraction pipeline remains completely unchanged and isolated.
- **Read-Only Data Lineage**: Prediction JSON files (`output/predictions/*.json`) are consumed strictly as read-only inputs.
- **Strict No-Fabrication Rule**: No guessing, hallucinating, or synthesizing candidate facts. If information is missing or ambiguous, it remains empty or `Unknown`.
- **Configurable Policies**: All recruiter criteria, gating switches, component weights, and cutoffs are externalized and runtime-configurable.
- **Deterministic Transparency**: Every decision is explainable with human-readable matched requirements, missing requirements, and score audit trails.
- **Provider-Agnostic LLM Layer**: Institutional and publication tier services are decoupled through abstract interfaces to allow interchangeable LLM backends or local taxonomies.
