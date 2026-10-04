from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from shortlisting.models.candidate import NormalizedCandidate
from shortlisting.models.evaluation import ComponentScores
from shortlisting.models.requirements import RecruiterRequirements

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "scoring_config.json"


class CandidateScorer:
    """
    Configurable scoring engine computing component-level scores for
    Education, Experience, and Publications, along with composite Overall Score.
    No weights or tier scores are hardcoded; all are ingested from configuration.
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

    def score(
        self, candidate: NormalizedCandidate, requirements: RecruiterRequirements
    ) -> Tuple[ComponentScores, Dict[str, Any]]:
        edu_score, edu_audit = self.score_education(candidate, requirements)
        exp_score, exp_audit = self.score_experience(candidate, requirements)
        pub_score, pub_audit = self.score_publications(candidate, requirements)

        weights = self.config.get("component_weights", {"education": 0.35, "experience": 0.35, "publications": 0.30})
        w_edu = float(weights.get("education", 0.35))
        w_exp = float(weights.get("experience", 0.35))
        w_pub = float(weights.get("publications", 0.30))

        # Normalize weights if sum != 1.0
        total_w = w_edu + w_exp + w_pub
        if total_w > 0:
            w_edu /= total_w
            w_exp /= total_w
            w_pub /= total_w

        overall = (w_edu * edu_score) + (w_exp * exp_score) + (w_pub * pub_score)

        audit = {
            "applied_weights": {"education": round(w_edu, 3), "experience": round(w_exp, 3), "publications": round(w_pub, 3)},
            "education_audit": edu_audit,
            "experience_audit": exp_audit,
            "publication_audit": pub_audit,
        }

        return ComponentScores(
            education_score=round(edu_score, 2),
            experience_score=round(exp_score, 2),
            publication_score=round(pub_score, 2),
            overall_score=round(overall, 2),
        ), audit

    # -------------------------------------------------------------------------
    # EDUCATION SCORING
    # -------------------------------------------------------------------------
    def score_education(
        self, candidate: NormalizedCandidate, requirements: RecruiterRequirements
    ) -> Tuple[float, Dict[str, Any]]:
        cfg_edu = self.config.get("education_scoring", {})
        tier_scores = self.config.get("tier_score_mapping", {}).get("university", {})

        w_deg = float(cfg_edu.get("degree_fulfillment_weight", 0.50))
        w_tier = float(cfg_edu.get("tier_quality_weight", 0.50))

        # 1. Degree fulfillment score
        cand_degrees = [e.degree for e in candidate.education if e.degree]
        req_degrees = requirements.education.required_degrees
        min_level = requirements.education.minimum_degree_level
        mode = requirements.education.degree_match_mode or "exact"

        deg_match = False
        from shortlisting.engine.matcher import RequirementMatcher

        if min_level:
            req_rank = RequirementMatcher.DEGREE_LEVEL_RANKS.get(min_level.lower().strip(), 1)
            cand_ranks = [RequirementMatcher.get_degree_level_rank(d) for d in cand_degrees]
            cand_max = max(cand_ranks) if cand_ranks else 0
            if cand_max >= req_rank:
                deg_match = True

        if not deg_match and req_degrees:
            for req_d in req_degrees:
                for cand_d in cand_degrees:
                    if RequirementMatcher.match_degree(req_d, cand_d, mode=mode):
                        deg_match = True
                        break
                if deg_match:
                    break

        if not min_level and not req_degrees:
            deg_score = 100.0 if cand_degrees else 50.0
        else:
            deg_score = 100.0 if deg_match else 20.0

        # 2. University Tier Aggregation
        method = requirements.education.tier_aggregation_method or cfg_edu.get("default_aggregation_method", "highest_degree")
        agg_tier_score = self._aggregate_university_tier(candidate.education, method, tier_scores, cfg_edu)

        final_edu = (w_deg * deg_score) + (w_tier * agg_tier_score)
        audit = {
            "degree_score": round(deg_score, 2),
            "tier_score": round(agg_tier_score, 2),
            "aggregation_method": method,
            "degree_match_mode": mode,
        }
        return min(100.0, max(0.0, final_edu)), audit

    def _aggregate_university_tier(
        self, entries: List[Any], method: str, tier_scores: Dict[str, float], cfg_edu: Dict[str, Any]
    ) -> float:
        if not entries:
            return float(tier_scores.get("Unknown", 10.0))

        # Convert each entry to tier points
        entry_scores = [float(tier_scores.get(e.university_tier, tier_scores.get("Unknown", 10.0))) for e in entries]

        if method == "average":
            return sum(entry_scores) / len(entry_scores)

        elif method == "minimum_tier":
            return min(entry_scores)

        elif method == "weighted_by_degree":
            weights = cfg_edu.get("degree_weights_for_aggregation", {"phd": 0.50, "masters": 0.30, "bachelors": 0.20})
            weighted_sum = 0.0
            sum_w = 0.0
            for e, score in zip(entries, entry_scores):
                deg_lower = e.degree.lower()
                if "phd" in deg_lower or "doctor" in deg_lower:
                    w = float(weights.get("phd", 0.50))
                elif "m" in deg_lower or "master" in deg_lower:
                    w = float(weights.get("masters", 0.30))
                else:
                    w = float(weights.get("bachelors", 0.20))
                weighted_sum += w * score
                sum_w += w
            return (weighted_sum / sum_w) if sum_w > 0 else (sum(entry_scores) / len(entry_scores))

        else:  # default: highest_degree
            for e, s in zip(entries, entry_scores):
                if any(k in e.degree.lower() for k in ["phd", "doctor"]):
                    return s
            for e, s in zip(entries, entry_scores):
                if any(k in e.degree.lower() for k in ["master", "m."]):
                    return s
            return entry_scores[0]

    # -------------------------------------------------------------------------
    # EXPERIENCE SCORING
    # -------------------------------------------------------------------------
    def score_experience(
        self, candidate: NormalizedCandidate, requirements: RecruiterRequirements
    ) -> Tuple[float, Dict[str, Any]]:
        cfg_exp = self.config.get("experience_scoring", {})
        w_dur = float(cfg_exp.get("duration_fulfillment_weight", 0.60))
        w_role = float(cfg_exp.get("role_relevance_weight", 0.40))

        valid_durations = [e.duration_years for e in candidate.experience if e.duration_years is not None]
        total_dur = sum(valid_durations)

        req_dur = requirements.experience.min_total_experience_years
        if req_dur <= 0:
            dur_score = 100.0 if total_dur > 0 else 50.0
        else:
            dur_score = min(100.0, (total_dur / req_dur) * 100.0)

        # Role relevance
        req_roles = [r.lower() for r in requirements.experience.relevant_roles]
        if not req_roles:
            role_score = 100.0 if candidate.experience else 50.0
        else:
            cand_roles = " ".join(e.job_title.lower() for e in candidate.experience)
            matched_roles = sum(1 for r in req_roles if r in cand_roles)
            role_score = min(100.0, (matched_roles / len(req_roles)) * 100.0)

        final_exp = (w_dur * dur_score) + (w_role * role_score)
        audit = {
            "total_duration_years": round(total_dur, 1),
            "duration_score": round(dur_score, 2),
            "role_relevance_score": round(role_score, 2),
        }
        return min(100.0, max(0.0, final_exp)), audit

    # -------------------------------------------------------------------------
    # PUBLICATION SCORING (SUBSET-ISOLATED TIER QUALITY & SEPARATE QUOTAS)
    # -------------------------------------------------------------------------
    def _compute_subset_tier_score(
        self,
        pubs: List[Any],
        required_tiers: List[str],
        tier_scores: Dict[str, float],
    ) -> float:
        if not pubs:
            return 0.0

        points = [float(tier_scores.get(p.tier, tier_scores.get("Unranked", 10.0))) for p in pubs]
        avg_points = sum(points) / len(points)

        if required_tiers:
            meets_count = sum(1 for p in pubs if p.tier in required_tiers)
            fulfillment_ratio = (meets_count / len(pubs)) * 100.0
            return min(100.0, max(0.0, (0.5 * avg_points) + (0.5 * fulfillment_ratio)))

        return min(100.0, max(0.0, avg_points))

    def score_publications(
        self, candidate: NormalizedCandidate, requirements: RecruiterRequirements
    ) -> Tuple[float, Dict[str, Any]]:
        cfg_pub = self.config.get("publication_scoring", {})
        tier_scores = self.config.get("tier_score_mapping", {}).get("publication", {})

        w_vol = float(cfg_pub.get("total_volume_weight", 0.25))
        w_jnl = float(cfg_pub.get("journal_fulfillment_weight", 0.30))
        w_cnf = float(cfg_pub.get("conference_fulfillment_weight", 0.15))
        w_tier = float(cfg_pub.get("tier_quality_weight", 0.20))
        w_rec = float(cfg_pub.get("recency_weight", 0.10))

        pub_req = requirements.publications

        cand_total = len(candidate.publications)
        journal_pubs = [p for p in candidate.publications if p.type == "journal"]
        conf_pubs = [p for p in candidate.publications if p.type == "conference"]
        cand_jnl = len(journal_pubs)
        cand_cnf = len(conf_pubs)

        # 1. Total Volume fulfillment
        if pub_req.min_total_publications > 0:
            vol_score = min(100.0, (cand_total / pub_req.min_total_publications) * 100.0)
        else:
            vol_score = 100.0 if cand_total > 0 else 50.0

        # 2. Journal fulfillment (Conference publications DO NOT contribute)
        if pub_req.min_journal_publications > 0:
            jnl_score = min(100.0, (cand_jnl / pub_req.min_journal_publications) * 100.0)
        else:
            jnl_score = 100.0 if cand_jnl > 0 else 60.0

        # 3. Conference fulfillment (Journal publications DO NOT contribute)
        if pub_req.min_conference_publications > 0:
            cnf_score = min(100.0, (cand_cnf / pub_req.min_conference_publications) * 100.0)
        else:
            cnf_score = 100.0 if cand_cnf > 0 else 60.0

        # 4. Subset-Isolated Tier Quality Scoring
        required_tiers = pub_req.required_publication_tiers
        jnl_tier_score = self._compute_subset_tier_score(journal_pubs, required_tiers, tier_scores)
        cnf_tier_score = self._compute_subset_tier_score(conf_pubs, required_tiers, tier_scores)

        # Determine relevant tier quality based on requirements
        applied_subset: str
        if pub_req.min_journal_publications > 0 and pub_req.min_conference_publications == 0:
            # Recruiter specifically requires journals: evaluate tier quality strictly on journals
            tier_score = jnl_tier_score
            applied_subset = "journals_only"
        elif pub_req.min_conference_publications > 0 and pub_req.min_journal_publications == 0:
            # Recruiter specifically requires conferences: evaluate tier quality strictly on conferences
            tier_score = cnf_tier_score
            applied_subset = "conferences_only"
        elif pub_req.min_journal_publications > 0 and pub_req.min_conference_publications > 0:
            # Both required: combine using configurable subset weights
            w_jnl_tier = float(cfg_pub.get("journal_tier_weight", 0.60))
            w_cnf_tier = float(cfg_pub.get("conference_tier_weight", 0.40))
            tier_score = (w_jnl_tier * jnl_tier_score + w_cnf_tier * cnf_tier_score) / (w_jnl_tier + w_cnf_tier)
            applied_subset = "journals_and_conferences_weighted"
        else:
            # Fallback: neither specifically targeted; evaluate across all candidate publications
            tier_score = self._compute_subset_tier_score(candidate.publications, required_tiers, tier_scores)
            applied_subset = "all_publications_fallback"

        # 5. Recency fulfillment
        if pub_req.recent_years_window is not None and pub_req.recent_years_window > 0:
            current_year = datetime.now().year
            cutoff_year = current_year - pub_req.recent_years_window
            recent_count = sum(
                1 for p in candidate.publications if p.year and str(p.year).isdigit() and int(p.year) >= cutoff_year
            )
            target_recent = pub_req.min_recent_publications if pub_req.min_recent_publications > 0 else max(1, cand_total)
            rec_score = min(100.0, (recent_count / target_recent) * 100.0) if cand_total > 0 else 0.0
        else:
            rec_score = 100.0 if cand_total > 0 else 50.0

        final_pub = (
            (w_vol * vol_score)
            + (w_jnl * jnl_score)
            + (w_cnf * cnf_score)
            + (w_tier * tier_score)
            + (w_rec * rec_score)
        )

        audit = {
            "total_publications": cand_total,
            "journal_publications": cand_jnl,
            "conference_publications": cand_cnf,
            "volume_score": round(vol_score, 2),
            "journal_score": round(jnl_score, 2),
            "conference_score": round(cnf_score, 2),
            "journal_tier_score": round(jnl_tier_score, 2),
            "conference_tier_score": round(cnf_tier_score, 2),
            "tier_score": round(tier_score, 2),
            "recency_score": round(rec_score, 2),
            "applied_tier_subset": applied_subset,
        }
        return min(100.0, max(0.0, final_pub)), audit
