from __future__ import annotations

from typing import Any, Dict, List

from shortlisting.models.evaluation import ShortlistDecision


class ExplainabilityReportBuilder:
    """
    Builds transparent, recruiter-facing explainability summaries for candidate evaluations.
    Strictly uses evidence from the normalized candidate profile and suppresses internal LLM reasoning,
    raw citations, venues, and DOIs.
    """

    @staticmethod
    def build_summary_text(decision: ShortlistDecision) -> str:
        s = decision.scores
        lines: List[str] = [
            f"### Shortlist Evaluation: {decision.candidate_name or '[Unknown Candidate]'}",
            f"**Decision**: `{decision.decision}` | **Overall Score**: `{s.overall_score}/100`",
            f"**Hard Gate Status**: `{'PASSED' if decision.hard_criteria_met else 'FAILED'}`",
            "",
            "#### Component Score Breakdown",
            f"- **Education Score**: `{s.education_score}/100`",
            f"- **Experience Score**: `{s.experience_score}/100`",
            f"- **Publication Score**: `{s.publication_score}/100`",
            "",
            "#### Matched Requirements",
        ]

        if decision.matched_requirements:
            for item in decision.matched_requirements:
                lines.append(f"- ✅ {item}")
        else:
            lines.append("- (None)")

        lines.append("")
        lines.append("#### Missing Requirements / Gaps")
        if decision.missing_requirements:
            for item in decision.missing_requirements:
                lines.append(f"- ❌ {item}")
        else:
            lines.append("- (None)")

        lines.append("")
        lines.append("#### Normalized Evidence Trace")
        lines.append("**Education**:")
        for e in decision.evidence.get("education", []):
            lines.append(f"  • {e}")

        lines.append("**Experience**:")
        for x in decision.evidence.get("experience", []):
            lines.append(f"  • {x}")

        lines.append("**Publications**:")
        for p in decision.evidence.get("publications", []):
            lines.append(f"  • {p}")

        return "\n".join(lines)

    @staticmethod
    def to_dict(decision: ShortlistDecision) -> Dict[str, Any]:
        return decision.to_dict()
