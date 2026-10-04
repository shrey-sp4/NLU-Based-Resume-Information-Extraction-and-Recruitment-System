from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from shortlisting.models.candidate import NormalizedCandidate
from shortlisting.models.requirements import RecruiterRequirements


class RequirementMatcher:
    """
    Evaluates a NormalizedCandidate against RecruiterRequirements across:
    Education, Experience, and Publications.
    Produces granular matched and missing requirements lists and checks hard gates.
    """

    DEGREE_LEVEL_RANKS: Dict[str, int] = {
        "doctorate": 3,
        "phd": 3,
        "masters": 2,
        "master": 2,
        "bachelors": 1,
        "bachelor": 1,
    }

    DEGREE_FAMILY_PATTERNS: Dict[str, List[str]] = {
        "phd": [r"\bph\.?d\b", r"\bdoctor of philosophy\b", r"\bd\.?phil\b", r"\bpost-?doctoral\b"],
        "mtech": [r"\bm\.?tech\b", r"\bmaster of technology\b", r"\bm\.?e\b", r"\bmaster of engineering\b"],
        "msc": [r"\bm\.?sc\b", r"\bmaster of science\b", r"\bm\.?s\b"],
        "ma": [r"\bm\.?a\b", r"\bmaster of arts\b", r"\bmaster in arts\b", r"\bmsw\b"],
        "btech": [r"\bb\.?tech\b", r"\bbachelor of technology\b", r"\bb\.?e\b", r"\bbachelor of engineering\b"],
        "bsc": [r"\bb\.?sc\b", r"\bbachelor of science\b", r"\bb\.?s\b"],
        "ba": [r"\bb\.?a\b", r"\bbachelor of arts\b"],
        "mba": [r"\bmba\b", r"\bmaster of business administration\b"],
        "mca": [r"\bmca\b", r"\bmaster of computer applications?\b"],
    }

    @classmethod
    def get_degree_level_rank(cls, degree_str: str) -> int:
        d = degree_str.lower()
        if any(re.search(p, d) for p in cls.DEGREE_FAMILY_PATTERNS["phd"]) or "doctor" in d:
            return 3
        if (
            any(
                re.search(p, d)
                for p in cls.DEGREE_FAMILY_PATTERNS["mtech"]
                + cls.DEGREE_FAMILY_PATTERNS["msc"]
                + cls.DEGREE_FAMILY_PATTERNS["ma"]
                + cls.DEGREE_FAMILY_PATTERNS["mba"]
                + cls.DEGREE_FAMILY_PATTERNS["mca"]
            )
            or "master" in d
            or "m." in d
        ):
            return 2
        if (
            any(
                re.search(p, d)
                for p in cls.DEGREE_FAMILY_PATTERNS["btech"]
                + cls.DEGREE_FAMILY_PATTERNS["bsc"]
                + cls.DEGREE_FAMILY_PATTERNS["ba"]
            )
            or "bachelor" in d
            or "b." in d
        ):
            return 1
        return 0

    @classmethod
    def match_degree(cls, required: str, candidate_deg: str, mode: str = "exact") -> bool:
        r_clean = required.lower().strip()
        c_clean = candidate_deg.lower().strip()

        if mode == "level_or_higher":
            req_rank = cls.get_degree_level_rank(r_clean)
            cand_rank = cls.get_degree_level_rank(c_clean)
            if req_rank > 0 and cand_rank >= req_rank:
                return True
            return r_clean in c_clean or c_clean in r_clean

        # Exact / Specific Degree Matching
        r_norm = re.sub(r"[^a-z0-9]", "", r_clean)
        c_norm = re.sub(r"[^a-z0-9]", "", c_clean)
        if r_norm == c_norm:
            return True

        # Check family match: both must belong to the exact same degree family
        for fam, patterns in cls.DEGREE_FAMILY_PATTERNS.items():
            r_in_fam = any(re.search(p, r_clean) for p in patterns)
            c_in_fam = any(re.search(p, c_clean) for p in patterns)
            if r_in_fam and c_in_fam:
                return True
            if (r_in_fam and not c_in_fam) or (c_in_fam and not r_in_fam):
                # If one belongs to this specific family and the other doesn't, they are not exact
                continue

        r_rank = cls.get_degree_level_rank(r_clean)
        c_rank = cls.get_degree_level_rank(c_clean)
        if r_rank > 0 and c_rank > 0 and r_rank == c_rank:
            if r_clean in c_clean or c_clean in r_clean:
                return True

        return False

    def match(
        self, candidate: NormalizedCandidate, requirements: RecruiterRequirements
    ) -> Dict[str, Any]:
        matched: List[str] = []
        missing: List[str] = []
        hard_gate_met = True

        # ----------------------------------------------------
        # 1. EDUCATION MATCHING
        # ----------------------------------------------------
        edu_req = requirements.education
        candidate_degrees = [e.degree for e in candidate.education if e.degree]
        candidate_tiers = [e.university_tier for e in candidate.education if e.university_tier]

        # 1. A. Minimum Degree Level
        if edu_req.minimum_degree_level:
            req_level_str = edu_req.minimum_degree_level.lower().strip()
            req_rank = self.DEGREE_LEVEL_RANKS.get(req_level_str, 1)
            cand_ranks = [self.get_degree_level_rank(d) for d in candidate_degrees]
            cand_max_rank = max(cand_ranks) if cand_ranks else 0

            if cand_max_rank >= req_rank:
                matched.append(
                    f"Satisfies minimum degree level '{edu_req.minimum_degree_level}' (highest degree rank {cand_max_rank})"
                )
            else:
                missing.append(
                    f"Does not meet minimum degree level requirement: '{edu_req.minimum_degree_level}'"
                )
                if edu_req.must_have_degree:
                    hard_gate_met = False

        # 1. B. Required Specific Degrees
        if edu_req.required_degrees:
            degree_found = False
            match_mode = edu_req.degree_match_mode or "exact"
            for req_deg in edu_req.required_degrees:
                for cand_deg in candidate_degrees:
                    if self.match_degree(req_deg, cand_deg, mode=match_mode):
                        degree_found = True
                        matched.append(f"Satisfies required degree '{req_deg}' with '{cand_deg}'")
                        break
                if degree_found:
                    break

            if not degree_found:
                missing.append(f"Missing required degree: {', '.join(edu_req.required_degrees)}")
                if edu_req.must_have_degree and not edu_req.minimum_degree_level:
                    hard_gate_met = False

        # 1. C. Stream Requirements (Three States: Match, Unverified, Conflict)
        if edu_req.required_streams:
            cand_streams = [e.stream.strip() for e in candidate.education if e.stream and e.stream.strip()]
            if not cand_streams:
                # State B: Missing / Unverified
                missing.append(
                    f"Stream information unverified in extracted profile for required stream(s): {', '.join(edu_req.required_streams)}"
                )
                if edu_req.must_verify_stream:
                    hard_gate_met = False
            else:
                stream_match = False
                for req_stream in edu_req.required_streams:
                    r_s = req_stream.lower().strip()
                    for c_s in cand_streams:
                        c_lower = c_s.lower().strip()
                        if r_s in c_lower or c_lower in r_s:
                            stream_match = True
                            matched.append(f"Satisfies required stream with '{c_s}'")
                            break
                    if stream_match:
                        break

                if not stream_match:
                    # State C: Explicit Conflict
                    missing.append(
                        f"Candidate stream '{', '.join(cand_streams)}' conflicts with required stream(s): {', '.join(edu_req.required_streams)}"
                    )
                    hard_gate_met = False if edu_req.must_verify_stream else hard_gate_met

        # 1. D. University Tiers
        if edu_req.preferred_university_tiers:
            tier_found = any(t in edu_req.preferred_university_tiers for t in candidate_tiers)
            if tier_found:
                matched.append(
                    f"Holds education at preferred tier: {', '.join(set(candidate_tiers) & set(edu_req.preferred_university_tiers))}"
                )
            else:
                missing.append(
                    f"Institution tier does not match preferred tiers: {', '.join(edu_req.preferred_university_tiers)}"
                )

        if edu_req.minimum_university_tier:
            if not self._meets_min_tier(candidate_tiers, edu_req.minimum_university_tier):
                missing.append(f"Does not meet minimum university tier requirement: {edu_req.minimum_university_tier}")
                hard_gate_met = False

        # ----------------------------------------------------
        # 2. EXPERIENCE MATCHING
        # ----------------------------------------------------
        exp_req = requirements.experience
        valid_durations = [e.duration_years for e in candidate.experience if e.duration_years is not None]
        total_duration = sum(valid_durations)

        academic_duration = sum(
            e.duration_years
            for e in candidate.experience
            if e.duration_years is not None and e.experience_type == "academic"
        )
        industry_duration = sum(
            e.duration_years
            for e in candidate.experience
            if e.duration_years is not None and e.experience_type == "industry"
        )

        if exp_req.min_total_experience_years > 0:
            if total_duration >= exp_req.min_total_experience_years:
                matched.append(
                    f"Total experience ({total_duration:.1f} yrs) meets minimum requirement ({exp_req.min_total_experience_years:.1f} yrs)"
                )
            else:
                missing.append(
                    f"Total experience ({total_duration:.1f} yrs) below requirement ({exp_req.min_total_experience_years:.1f} yrs)"
                )
                if exp_req.must_meet_min_experience:
                    hard_gate_met = False

        if exp_req.min_academic_experience_years > 0:
            if academic_duration >= exp_req.min_academic_experience_years:
                matched.append(
                    f"Academic experience ({academic_duration:.1f} yrs) meets minimum ({exp_req.min_academic_experience_years:.1f} yrs)"
                )
            else:
                missing.append(
                    f"Academic experience ({academic_duration:.1f} yrs) below requirement ({exp_req.min_academic_experience_years:.1f} yrs)"
                )

        if exp_req.min_industry_experience_years > 0:
            if industry_duration >= exp_req.min_industry_experience_years:
                matched.append(
                    f"Industry experience ({industry_duration:.1f} yrs) meets minimum ({exp_req.min_industry_experience_years:.1f} yrs)"
                )
            else:
                missing.append(
                    f"Industry experience ({industry_duration:.1f} yrs) below requirement ({exp_req.min_industry_experience_years:.1f} yrs)"
                )

        if exp_req.relevant_roles:
            cand_roles = " ".join(e.job_title.lower() for e in candidate.experience)
            matched_roles = [r for r in exp_req.relevant_roles if r.lower() in cand_roles]
            if matched_roles:
                matched.append(f"Demonstrates relevant role experience: {', '.join(matched_roles)}")
            else:
                missing.append(f"Lacks specific experience in target roles: {', '.join(exp_req.relevant_roles)}")

        # ----------------------------------------------------
        # 3. PUBLICATION MATCHING (INDEPENDENT HARD GATES)
        # ----------------------------------------------------
        pub_req = requirements.publications
        total_pubs = len(candidate.publications)
        journal_pubs = sum(1 for p in candidate.publications if p.type == "journal")
        conf_pubs = sum(1 for p in candidate.publications if p.type == "conference")

        # 3. A. Total publications
        if pub_req.min_total_publications > 0:
            if total_pubs >= pub_req.min_total_publications:
                matched.append(f"Total publications ({total_pubs}) meets requirement ({pub_req.min_total_publications})")
            else:
                missing.append(f"Total publications ({total_pubs}) below requirement ({pub_req.min_total_publications})")
                if pub_req.must_have_min_total:
                    hard_gate_met = False

        # 3. B. Journal publications
        if pub_req.min_journal_publications > 0:
            if journal_pubs >= pub_req.min_journal_publications:
                matched.append(f"Journal publications ({journal_pubs}) meets requirement ({pub_req.min_journal_publications})")
            else:
                missing.append(f"Journal publications ({journal_pubs}) below requirement ({pub_req.min_journal_publications})")
                if pub_req.must_have_min_journals:
                    hard_gate_met = False

        # 3. C. Conference publications
        if pub_req.min_conference_publications > 0:
            if conf_pubs >= pub_req.min_conference_publications:
                matched.append(f"Conference publications ({conf_pubs}) meets requirement ({pub_req.min_conference_publications})")
            else:
                missing.append(f"Conference publications ({conf_pubs}) below requirement ({pub_req.min_conference_publications})")
                if pub_req.must_have_min_conferences:
                    hard_gate_met = False

        # 3. D. Tier-1 publications
        if pub_req.min_tier1_publications > 0:
            tier1_count = sum(1 for p in candidate.publications if p.tier == "Tier-1")
            if tier1_count >= pub_req.min_tier1_publications:
                matched.append(f"Tier-1 publications ({tier1_count}) meets requirement ({pub_req.min_tier1_publications})")
            else:
                missing.append(f"Tier-1 publications ({tier1_count}) below requirement ({pub_req.min_tier1_publications})")
                if pub_req.must_have_min_tier1:
                    hard_gate_met = False

        # 3. E. Recent publications
        if pub_req.recent_years_window is not None and pub_req.recent_years_window > 0:
            current_year = datetime.now().year
            cutoff_year = current_year - pub_req.recent_years_window
            recent_count = sum(
                1 for p in candidate.publications if p.year and str(p.year).isdigit() and int(p.year) >= cutoff_year
            )
            if pub_req.min_recent_publications > 0:
                if recent_count >= pub_req.min_recent_publications:
                    matched.append(
                        f"Recent publications within {pub_req.recent_years_window} years ({recent_count}) meets requirement ({pub_req.min_recent_publications})"
                    )
                else:
                    missing.append(
                        f"Recent publications within {pub_req.recent_years_window} years ({recent_count}) below requirement ({pub_req.min_recent_publications})"
                    )
                    if pub_req.must_have_min_recent:
                        hard_gate_met = False
            else:
                matched.append(f"Recent publications within {pub_req.recent_years_window} years (since {cutoff_year}): {recent_count}")

        return {
            "hard_criteria_met": hard_gate_met,
            "matched_requirements": matched,
            "missing_requirements": missing,
        }

    def _degree_matches(self, required: str, candidate_deg: str) -> bool:
        return self.match_degree(required, candidate_deg, mode="exact")

    def _meets_min_tier(self, candidate_tiers: List[str], min_tier: str) -> bool:
        tier_ranks = {"Tier-1": 1, "Tier-2": 2, "Tier-3": 3, "Unknown": 4}
        req_rank = tier_ranks.get(min_tier, 4)
        for t in candidate_tiers:
            if tier_ranks.get(t, 4) <= req_rank:
                return True
        return False
