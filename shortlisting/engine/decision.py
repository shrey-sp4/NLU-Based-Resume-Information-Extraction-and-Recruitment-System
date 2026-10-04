from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from shortlisting.models.candidate import NormalizedCandidate
from shortlisting.models.evaluation import ComponentScores, ShortlistDecision
from shortlisting.models.requirements import RecruiterRequirements

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring_config.json"


class DecisionEngine:
    """
    Evaluates candidate matching results and component scores against
    configurable decision thresholds and hard-gate criteria.
    """

    def __init__(self, config_path: Optional[Path] = None, custom_config: Optional[Dict[str, Any]] = None):
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load_config(custom_config)

    def _load_config(self, custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        if self.config_path.exists():
            cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
        if custom_config:
            cfg.update(custom_config)
        return cfg

    def decide(
        self,
        candidate: NormalizedCandidate,
        scores: ComponentScores,
        match_result: Dict[str, Any],
        scoring_audit: Dict[str, Any],
    ) -> ShortlistDecision:
        thresholds = self.config.get("decision_thresholds", {"shortlist_cutoff": 75.0, "review_cutoff": 60.0})
        shortlist_cutoff = float(thresholds.get("shortlist_cutoff", 75.0))
        review_cutoff = float(thresholds.get("review_cutoff", 60.0))

        hard_criteria_met = bool(match_result.get("hard_criteria_met", True))
        overall = scores.overall_score

        if not hard_criteria_met:
            decision = "REJECTED"
        elif overall >= shortlist_cutoff:
            decision = "SHORTLISTED"
        elif overall >= review_cutoff:
            decision = "REVIEW"
        else:
            decision = "REJECTED"

        # Construct evidence strictly from normalized candidate fields
        evidence: Dict[str, List[str]] = {
            "education": [
                f"Degree: '{e.degree}', Institution: '{e.institution}', Tier: '{e.university_tier}'"
                for e in candidate.education
            ],
            "experience": [
                f"Role: '{e.job_title}', Org: '{e.institution}', Type: '{e.experience_type}', Duration: {f'{e.duration_years:.1f} yrs' if e.duration_years is not None else 'Unknown'}"
                for e in candidate.experience
            ],
            "publications": [
                f"Title: '{p.title or '[Unidentified]'}', Type: '{p.type}', Year: '{p.year or '[Unidentified]'}', Tier: '{p.tier}'"
                for p in candidate.publications[:8]  # Limit to first 8 for concise evidence
            ],
        }

        audit = dict(scoring_audit)
        audit["decision_thresholds"] = {"shortlist_cutoff": shortlist_cutoff, "review_cutoff": review_cutoff}

        return ShortlistDecision(
            candidate_name=candidate.candidate_name,
            scores=scores,
            decision=decision,
            hard_criteria_met=hard_criteria_met,
            matched_requirements=match_result.get("matched_requirements", []),
            missing_requirements=match_result.get("missing_requirements", []),
            evidence=evidence,
            scoring_audit=audit,
        )
