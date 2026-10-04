from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ComponentScores:
    education_score: float = 0.0
    experience_score: float = 0.0
    publication_score: float = 0.0
    overall_score: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "education_score": round(self.education_score, 2),
            "experience_score": round(self.experience_score, 2),
            "publication_score": round(self.publication_score, 2),
            "overall_score": round(self.overall_score, 2),
        }


@dataclass
class ShortlistDecision:
    candidate_name: Optional[str] = ""
    scores: ComponentScores = field(default_factory=ComponentScores)
    decision: str = "REJECTED"  # SHORTLISTED | REVIEW | REJECTED
    hard_criteria_met: bool = True
    matched_requirements: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    evidence: Dict[str, List[str]] = field(default_factory=dict)
    scoring_audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name or "",
            "scores": self.scores.to_dict(),
            "decision": self.decision,
            "hard_criteria_met": self.hard_criteria_met,
            "matched_requirements": self.matched_requirements,
            "missing_requirements": self.missing_requirements,
            "evidence": self.evidence,
            "scoring_audit": self.scoring_audit,
        }
