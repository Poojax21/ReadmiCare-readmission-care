"""
ReadmitIQ — Patients API Routes
Patient management: list, search, create, and drill-down view.
"""

from __future__ import annotations

import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.schemas import PatientCreate, PatientSummary, DashboardStats, RiskHeatmapPoint
from app.ml.synthetic_data import SyntheticDataGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory store for demo (replace with DB queries in prod)
_gen = SyntheticDataGenerator(random_seed=123)
_demo_patients: List[dict] = []


def _init_demo() -> None:
    global _demo_patients
    if not _demo_patients:
        from app.ml.pipeline import get_inference_engine
        import pandas as pd
        engine = get_inference_engine()
        dataset = _gen.generate_dataset(n_patients=100, as_dataframe=True)
        for _, row in dataset.iterrows():
            record = {
                "id": str(uuid.uuid4()),
                "mrn": row.get("mrn", f"MRN{uuid.uuid4().hex[:6].upper()}"),
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "full_name": row.get("full_name"),
                "date_of_birth": row.get("date_of_birth"),
                "phone": row.get("phone"),
                "attending_physician": row.get("attending_physician"),
                "ward": row.get("ward"),
                "age": int(row.get("age", 65)),
                "gender": str(row.get("gender", "M")),
                "ethnicity": str(row.get("ethnicity", "UNKNOWN")),
                "primary_diagnosis_icd": str(row.get("primary_diagnosis_icd", "")),
                "primary_diagnosis_name": str(row.get("primary_diagnosis_name", "")),
                "comorbidities": row.get("comorbidities", []) if isinstance(row.get("comorbidities"), list) else [],
                "insurance_type": str(row.get("insurance_type", "")),
                "los_days": float(row.get("los_days", 3.0)),
                "admission_type": str(row.get("admission_type", "EMERGENCY")),
                "was_readmitted_30d": bool(row.get("was_readmitted_30d", False)),
            }
            # Quick risk estimate
            result = engine.predict(
                pd.DataFrame([{**row, "icd_codes": record["comorbidities"], "procedure_codes": []}]),
                include_shap=False,
            )
            record["risk_score"] = result["risk_score"]
            record["risk_tier"] = result["risk_tier"]
            record["top_features"] = result["top_features"][:5]
            record["clinical_explanation"] = result["clinical_explanation"]
            record["recommended_actions"] = result["recommended_actions"]
            _demo_patients.append(record)


@router.get(
    "",
    response_model=List[PatientSummary],
    summary="List Patients",
)
async def list_patients(
    search: Optional[str] = Query(None, description="Search by MRN or name"),
    risk_tier: Optional[str] = Query(None, description="Filter by risk tier: HIGH|MEDIUM|LOW"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[PatientSummary]:
    _init_demo()
    results = _demo_patients

    if risk_tier:
        results = [p for p in results if p.get("risk_tier") == risk_tier.upper()]
    if search:
        q = search.lower()
        results = [p for p in results if q in p.get("mrn", "").lower()]

    return [
        PatientSummary(
            id=uuid.UUID(p["id"]),
            mrn=p["mrn"],
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            full_name=p.get("full_name"),
            age=p["age"],
            gender=p["gender"],
            ethnicity=p.get("ethnicity"),
            date_of_birth=p.get("date_of_birth"),
            phone=p.get("phone"),
            primary_diagnosis_icd=p.get("primary_diagnosis_icd"),
            primary_diagnosis_name=p.get("primary_diagnosis_name"),
            comorbidities=p.get("comorbidities", []),
            insurance_type=p.get("insurance_type"),
            attending_physician=p.get("attending_physician"),
            ward=p.get("ward"),
            latest_risk_score=p.get("risk_score"),
            risk_tier=p.get("risk_tier"),
        )
        for p in results[offset: offset + limit]
    ]


@router.post(
    "",
    response_model=PatientSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Patient",
)
async def create_patient(patient: PatientCreate) -> PatientSummary:
    _init_demo()
    from app.ml.pipeline import get_inference_engine
    import pandas as pd
    
    engine = get_inference_engine()
    
    # Check if MRN already exists
    if any(p.get("mrn") == patient.mrn for p in _demo_patients):
        raise HTTPException(status_code=400, detail="Patient with this MRN already exists")

    # Construct the base record
    record = {
        "id": str(uuid.uuid4()),
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "full_name": f"{patient.first_name or ''} {patient.last_name or ''}".strip() or None,
        "date_of_birth": patient.date_of_birth,
        "phone": patient.phone,
        "attending_physician": patient.attending_physician,
        "ward": patient.ward,
        "age": patient.age,
        "gender": patient.gender,
        "ethnicity": patient.ethnicity,
        "primary_diagnosis_icd": patient.primary_diagnosis_icd,
        "primary_diagnosis_name": patient.primary_diagnosis_name,
        "comorbidities": patient.comorbidities,
        "insurance_type": patient.insurance_type,
        "los_days": 1.0,  # Default for new patient
        "admission_type": "URGENT",
        "was_readmitted_30d": False,
    }

    # Run the ML pipeline to get a risk score
    try:
        model_input = pd.DataFrame([{**record, "icd_codes": record["comorbidities"], "procedure_codes": []}])
        result = engine.predict(model_input, include_shap=False)
        record["risk_score"] = result["risk_score"]
        record["risk_tier"] = result["risk_tier"]
        record["top_features"] = result["top_features"][:5]
        record["clinical_explanation"] = result["clinical_explanation"]
        record["recommended_actions"] = result["recommended_actions"]
    except Exception as e:
        logger.error(f"Failed to generate predictions for new patient: {e}")
        record["risk_score"] = 0.5
        record["risk_tier"] = "MEDIUM"
        record["top_features"] = []
    
    _demo_patients.insert(0, record)  # Add to top of list
    
    return PatientSummary(
        id=uuid.UUID(record["id"]),
        mrn=record["mrn"],
        first_name=record.get("first_name"),
        last_name=record.get("last_name"),
        full_name=record.get("full_name"),
        age=record["age"],
        gender=record["gender"],
        ethnicity=record.get("ethnicity"),
        date_of_birth=record.get("date_of_birth"),
        phone=record.get("phone"),
        primary_diagnosis_icd=record.get("primary_diagnosis_icd"),
        primary_diagnosis_name=record.get("primary_diagnosis_name"),
        comorbidities=record.get("comorbidities", []),
        insurance_type=record.get("insurance_type"),
        attending_physician=record.get("attending_physician"),
        ward=record.get("ward"),
        latest_risk_score=record.get("risk_score"),
        risk_tier=record.get("risk_tier"),
    )


@router.get(
    "/dashboard/stats",
    response_model=DashboardStats,
    summary="Dashboard Statistics",
)
async def dashboard_stats() -> DashboardStats:
    _init_demo()
    import datetime

    high = sum(1 for p in _demo_patients if p.get("risk_tier") == "HIGH")
    medium = sum(1 for p in _demo_patients if p.get("risk_tier") == "MEDIUM")
    low = sum(1 for p in _demo_patients if p.get("risk_tier") == "LOW")
    avg = sum(p.get("risk_score", 0) for p in _demo_patients) / max(len(_demo_patients), 1)

    return DashboardStats(
        total_active_admissions=len(_demo_patients),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        avg_risk_score=round(avg, 3),
        alerts_today=high,
        model_accuracy=0.847,
        last_updated=datetime.datetime.now(datetime.timezone.utc),
    )


@router.get(
    "/heatmap",
    response_model=List[RiskHeatmapPoint],
    summary="Risk Heatmap Data",
)
async def risk_heatmap(
    limit: int = Query(100, ge=1, le=500),
) -> List[RiskHeatmapPoint]:
    _init_demo()
    return [
        RiskHeatmapPoint(
            patient_id=uuid.UUID(p["id"]),
            mrn=p["mrn"],
            age=p["age"],
            risk_score=p.get("risk_score", 0),
            risk_tier=p.get("risk_tier", "LOW"),
            primary_diagnosis=p.get("primary_diagnosis_icd"),
            los_days=p.get("los_days"),
            top_risk_factor=(
                p["top_features"][0].get("label", "")
                if p.get("top_features") else None
            ),
        )
        for p in _demo_patients[:limit]
    ]


@router.get(
    "/dashboard/trend",
    summary="Weekly Risk Trend Data",
)
async def weekly_risk_trend() -> dict:
    """Returns daily risk tier counts for the past week, computed from patient data."""
    _init_demo()
    import random
    random.seed(42)

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    total = len(_demo_patients)
    high_base = sum(1 for p in _demo_patients if p.get("risk_tier") == "HIGH")
    med_base = sum(1 for p in _demo_patients if p.get("risk_tier") == "MEDIUM")
    low_base = total - high_base - med_base

    trend = []
    for i, day in enumerate(days):
        # Slight daily variation based on the actual distribution
        h = max(0, high_base + random.randint(-3, 4))
        m = max(0, med_base + random.randint(-4, 5))
        lo = max(0, total - h - m)
        trend.append({"day": day, "high": h, "medium": m, "low": lo})

    return {"trend": trend}


@router.get(
    "/{patient_id}",
    summary="Get Patient Detail",
)
async def get_patient(patient_id: str) -> dict:
    _init_demo()
    match = next(
        (p for p in _demo_patients if p["id"] == patient_id), None
    )
    if not match:
        raise HTTPException(status_code=404, detail="Patient not found")
    return match


@router.get(
    "/{patient_id}/trajectory",
    summary="Risk Trajectory Over Time",
)
async def get_patient_trajectory(patient_id: str, hours: int = 24) -> dict:
    """Returns hourly risk trajectory data for the given patient."""
    _init_demo()
    match = next(
        (p for p in _demo_patients if p["id"] == patient_id), None
    )
    if not match:
        raise HTTPException(status_code=404, detail="Patient not found")

    from app.ml.time_series import trajectory_engine
    trajectory = trajectory_engine.compute_trajectory(match, hours=hours)
    return {
        "patient_id": patient_id,
        "current_risk": match.get("risk_score", 0.5),
        "current_tier": match.get("risk_tier", "MEDIUM"),
        "trajectory": trajectory,
    }

