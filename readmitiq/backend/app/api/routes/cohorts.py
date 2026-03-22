"""
ReadmitIQ — Cohort Analysis Routes
Filtered patient cohorts with aggregate statistics.
"""

from fastapi import APIRouter, Query
from app.schemas.schemas import CohortFilter, CohortSummary

router = APIRouter()


@router.post("", response_model=CohortSummary, summary="Analyze Patient Cohort")
async def analyze_cohort(filters: CohortFilter) -> CohortSummary:
    """Return aggregated statistics for a filtered patient cohort."""
    from app.api.routes.patients import _demo_patients, _init_demo
    _init_demo()

    cohort = _demo_patients

    if filters.risk_tier:
        tiers = [t.upper() for t in filters.risk_tier]
        cohort = [p for p in cohort if p.get("risk_tier") in tiers]
    if filters.age_min is not None:
        cohort = [p for p in cohort if p.get("age", 0) >= filters.age_min]
    if filters.age_max is not None:
        cohort = [p for p in cohort if p.get("age", 999) <= filters.age_max]

    if not cohort:
        return CohortSummary(
            total_patients=0, high_risk=0, medium_risk=0, low_risk=0,
            avg_risk_score=0.0, avg_age=0.0, avg_los=0.0, top_diagnoses=[],
        )

    from collections import Counter
    diag_counts = Counter(p.get("primary_diagnosis_icd", "") for p in cohort)
    top_dx = [{"code": k, "count": v} for k, v in diag_counts.most_common(5)]

    return CohortSummary(
        total_patients=len(cohort),
        high_risk=sum(1 for p in cohort if p.get("risk_tier") == "HIGH"),
        medium_risk=sum(1 for p in cohort if p.get("risk_tier") == "MEDIUM"),
        low_risk=sum(1 for p in cohort if p.get("risk_tier") == "LOW"),
        avg_risk_score=round(sum(p.get("risk_score", 0) for p in cohort) / len(cohort), 3),
        avg_age=round(sum(p.get("age", 0) for p in cohort) / len(cohort), 1),
        avg_los=round(sum(p.get("los_days", 0) for p in cohort) / len(cohort), 1),
        top_diagnoses=top_dx,
        readmission_rate_actual=round(
            sum(1 for p in cohort if p.get("was_readmitted_30d", False)) / len(cohort), 3
        ),
    )
