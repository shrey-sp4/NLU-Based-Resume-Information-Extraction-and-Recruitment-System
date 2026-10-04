from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from shortlisting.engine.decision import DecisionEngine
from shortlisting.engine.matcher import RequirementMatcher
from shortlisting.engine.scorer import CandidateScorer
from shortlisting.models.candidate import NormalizedCandidate
from shortlisting.models.requirements import (
    EducationRequirements,
    ExperienceRequirements,
    PublicationRequirements,
    RecruiterRequirements,
)
from shortlisting.normalization.candidate_normalizer import CandidateNormalizer
from shortlisting.reporting.explainability import ExplainabilityReportBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_DIR = PROJECT_ROOT / "output" / "predictions"


def load_candidate_predictions() -> Dict[str, Path]:
    """Scans and returns map of candidate filename to file path."""
    if not PREDICTIONS_DIR.exists():
        return {}
    return {p.name: p for p in sorted(PREDICTIONS_DIR.glob("*.json"))}


def main():
    st.set_page_config(page_title="Academic & Faculty Resume Shortlisting System", layout="wide")
    st.title("🎯 Recruiter Resume Shortlisting System")
    st.caption("Layered on top of NLU Robust Extraction Pipeline (Consuming output/predictions/*.json)")

    pred_files_map = load_candidate_predictions()
    if not pred_files_map:
        st.error(f"No prediction JSON files found in `{PREDICTIONS_DIR}`.")
        return

    # -------------------------------------------------------------
    # SIDEBAR: RECRUITER JOB REQUIREMENTS & CONFIGURABLE WEIGHTS
    # -------------------------------------------------------------
    with st.sidebar:
        st.header("📋 Recruiter Requirements")

        job_title = st.text_input("Target Job Title", value="Assistant Professor / Researcher")

        # 1. Education Criteria
        st.subheader("1. Education Criteria")
        req_degrees = st.multiselect(
            "Required Degrees",
            options=["Ph.D", "Doctor of Philosophy", "M.Tech", "M.Sc", "B.Tech", "B.Sc"],
            default=["Ph.D"],
        )
        pref_tiers = st.multiselect(
            "Preferred University Tiers",
            options=["Tier-1", "Tier-2", "Tier-3"],
            default=["Tier-1", "Tier-2"],
        )
        tier_agg = st.selectbox(
            "University Tier Aggregation Method",
            options=["highest_degree", "weighted_by_degree", "average", "minimum_tier"],
            index=0,
            help="Configurable aggregation strategy across multiple degrees held by candidate.",
        )
        must_have_degree = st.checkbox("Mandatory Degree (Hard Gate)", value=True)

        # 2. Experience Criteria
        st.subheader("2. Experience Criteria")
        min_total_exp = st.slider("Minimum Total Experience (Years)", 0.0, 15.0, 2.0, step=0.5)
        min_acad_exp = st.slider("Minimum Academic Experience (Years)", 0.0, 15.0, 2.0, step=0.5)
        min_ind_exp = st.slider("Minimum Industry Experience (Years)", 0.0, 10.0, 0.0, step=0.5)
        must_have_exp = st.checkbox("Mandatory Experience (Hard Gate)", value=False)

        # 3. Publication Criteria
        st.subheader("3. Publication Criteria")
        min_total_pubs = st.number_input("Minimum Total Publications", min_value=0, value=3)
        min_jnl_pubs = st.number_input("Minimum Journal Publications", min_value=0, value=2)
        min_cnf_pubs = st.number_input("Minimum Conference Publications", min_value=0, value=1)
        min_tier1_pubs = st.number_input("Minimum Tier-1 Publications", min_value=0, value=0)
        recent_years = st.slider("Recent Years Window (e.g. last N yrs)", 0, 10, 5)
        must_have_pubs = st.checkbox("Mandatory Publication Count (Hard Gate)", value=False)

        st.divider()
        st.subheader("⚖️ Configurable Scoring Weights (Defaults)")
        st.caption("Adjustable component weights (must sum to 100%)")
        w_edu = st.slider("Education Weight (%)", 0, 100, 35)
        w_exp = st.slider("Experience Weight (%)", 0, 100, 35)
        w_pub = st.slider("Publications Weight (%)", 0, 100, 30)

        st.subheader("🎯 Decision Thresholds")
        shortlist_cutoff = st.slider("Shortlist Cutoff Score", 50.0, 100.0, 75.0, step=1.0)
        review_cutoff = st.slider("Review Cutoff Score", 30.0, 90.0, 60.0, step=1.0)

    # Build Recruiter Requirements Object
    requirements = RecruiterRequirements(
        job_title=job_title,
        education=EducationRequirements(
            required_degrees=req_degrees,
            preferred_university_tiers=pref_tiers,
            tier_aggregation_method=tier_agg,
            must_have_degree=must_have_degree,
        ),
        experience=ExperienceRequirements(
            min_total_experience_years=min_total_exp,
            min_academic_experience_years=min_acad_exp,
            min_industry_experience_years=min_ind_exp,
            relevant_roles=["Assistant Professor", "Researcher", "Scientist", "Post-doctoral"],
            must_meet_min_experience=must_have_exp,
        ),
        publications=PublicationRequirements(
            min_total_publications=min_total_pubs,
            min_journal_publications=min_jnl_pubs,
            min_conference_publications=min_cnf_pubs,
            min_tier1_publications=min_tier1_pubs,
            recent_years_window=recent_years if recent_years > 0 else None,
            must_have_min_publications=must_have_pubs,
        ),
    )

    custom_scoring_config = {
        "component_weights": {
            "education": w_edu / 100.0,
            "experience": w_exp / 100.0,
            "publications": w_pub / 100.0,
        },
        "decision_thresholds": {
            "shortlist_cutoff": shortlist_cutoff,
            "review_cutoff": review_cutoff,
        },
    }

    # -------------------------------------------------------------
    # MAIN PANEL: EVALUATION ENGINE EXECUTION
    # -------------------------------------------------------------
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"Evaluating **{len(pred_files_map)}** candidate files from `output/predictions/` against `{job_title}` requirements.")
    with col2:
        run_btn = st.button("🚀 Run Shortlisting Evaluation", type="primary", use_container_width=True)

    normalizer = CandidateNormalizer()
    matcher = RequirementMatcher()
    scorer = CandidateScorer(custom_config=custom_scoring_config)
    decision_engine = DecisionEngine(custom_config=custom_scoring_config)

    # Process all candidates
    with st.spinner("Processing candidate profiles through shortlisting pipeline..."):
        decisions: List[Any] = []
        candidates_map: Dict[str, NormalizedCandidate] = {}

        for filename, filepath in pred_files_map.items():
            candidate = normalizer.normalize_file(filepath)
            candidates_map[filename] = candidate

            match_res = matcher.match(candidate, requirements)
            scores, audit = scorer.score(candidate, requirements)
            dec = decision_engine.decide(candidate, scores, match_res, audit)
            decisions.append((filename, candidate, dec))

    # Sort candidates by overall score descending
    decisions.sort(key=lambda item: item[2].scores.overall_score, reverse=True)

    # Summary metrics
    n_shortlisted = sum(1 for _, _, d in decisions if d.decision == "SHORTLISTED")
    n_review = sum(1 for _, _, d in decisions if d.decision == "REVIEW")
    n_rejected = sum(1 for _, _, d in decisions if d.decision == "REJECTED")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Candidates Audited", len(decisions))
    m2.metric("✅ Shortlisted", n_shortlisted)
    m3.metric("⚠️ Needs Review", n_review)
    m4.metric("❌ Rejected", n_rejected)

    st.divider()

    # Candidates Leaderboard Table
    st.subheader("📊 Candidate Ranking & Shortlist Leaderboard")

    table_rows = []
    for rank, (fname, cand, dec) in enumerate(decisions, start=1):
        s = dec.scores
        table_rows.append({
            "Rank": rank,
            "Candidate Name": cand.candidate_name or f"[Unknown: {fname}]",
            "Decision": dec.decision,
            "Overall Score": s.overall_score,
            "Education": s.education_score,
            "Experience": s.experience_score,
            "Publications": s.publication_score,
            "Hard Gate": "PASS" if dec.hard_criteria_met else "FAIL",
            "File": fname,
        })

    df = pd.DataFrame(table_rows)

    def color_decision(val):
        if val == "SHORTLISTED":
            return "color: #4ade80; font-weight: bold"
        elif val == "REVIEW":
            return "color: #fbbf24; font-weight: bold"
        else:
            return "color: #f87171"

    st.dataframe(
        df.style.applymap(color_decision, subset=["Decision"]),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # Granular Candidate Deep-Dive
    st.subheader("🔍 Candidate Explainability & Evidence Inspector")
    candidate_choices = [f"{row['Rank']}. {row['Candidate Name']} ({row['File']})" for row in table_rows]
    selected_choice = st.selectbox("Select Candidate to Inspect:", candidate_choices)

    if selected_choice:
        selected_rank = int(selected_choice.split(".")[0]) - 1
        sel_fname, sel_cand, sel_dec = decisions[selected_rank]

        t1, t2, t3 = st.tabs(["📝 Explainability Summary", "👤 Normalized Candidate Profile", "⚙️ Scoring Audit"])

        with t1:
            st.markdown(ExplainabilityReportBuilder.build_summary_text(sel_dec))

        with t2:
            st.write("Strictly normalized candidate data (skills, CGPA, venues, raw citations omitted):")
            st.json(sel_cand.to_dict())

        with t3:
            st.write("Configurable scoring weights, aggregation method, and sub-score components applied:")
            st.json(sel_dec.scoring_audit)


if __name__ == "__main__":
    main()
