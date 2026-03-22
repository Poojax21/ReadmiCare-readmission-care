"""
ReadmitIQ — Prediction API Routes
Handles single and batch readmission risk predictions.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.schemas.schemas import (
    PredictionRequest, PredictionResponse, BatchPredictionRequest,
    BatchPredictionResponse, FeatureImportance,
)
from app.ml.pipeline import get_inference_engine
from app.ml.synthetic_data import SyntheticDataGenerator
from app.core.security import require_permission, audit_log

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_patient_df(request: PredictionRequest) -> pd.DataFrame:
    """Convert API request to DataFrame for ML pipeline."""
    if request.patient_data:
        pd_data = request.patient_data
        # Aggregate vitals
        vitals = pd_data.vitals or []
        labs = pd_data.labs or []

        def agg_vitals(field: str, agg: str = "mean"):
            vals = [getattr(v, field) for v in vitals if getattr(v, field) is not None]
            if not vals:
                return None
            return {"mean": sum(vals)/len(vals), "min": min(vals), "max": max(vals), "std": float(pd.Series(vals).std())}[agg]

        def lab_agg(label: str, agg: str = "max"):
            vals = [l.value for l in labs if l.label.lower() == label.lower() and l.value is not None]
            if not vals:
                return None
            return {"max": max(vals), "min": min(vals), "mean": sum(vals)/len(vals)}[agg]

        record = {
            "age": 65,  # Would come from patient record
            "gender": "M",
            "los_days": 3.0,
            "admission_type": pd_data.admission_type or "EMERGENCY",
            "icd_codes": pd_data.icd_codes,
            "procedure_codes": pd_data.procedure_codes,
            "admit_time": pd_data.admit_time,
            # Vitals
            "heart_rate_mean": agg_vitals("heart_rate", "mean"),
            "heart_rate_min": agg_vitals("heart_rate", "min"),
            "heart_rate_max": agg_vitals("heart_rate", "max"),
            "heart_rate_std": agg_vitals("heart_rate", "std"),
            "systolic_bp_mean": agg_vitals("systolic_bp", "mean"),
            "systolic_bp_min": agg_vitals("systolic_bp", "min"),
            "diastolic_bp_mean": agg_vitals("diastolic_bp", "mean"),
            "resp_rate_mean": agg_vitals("respiratory_rate", "mean"),
            "resp_rate_max": agg_vitals("respiratory_rate", "max"),
            "temp_mean": agg_vitals("temperature", "mean"),
            "temp_min": agg_vitals("temperature", "min"),
            "temp_max": agg_vitals("temperature", "max"),
            "spo2_mean": agg_vitals("spo2", "mean"),
            "spo2_min": agg_vitals("spo2", "min"),
            "gcs_min": agg_vitals("gcs_total", "min"),
            # Labs
            "creatinine_max": lab_agg("creatinine", "max"),
            "creatinine_mean": lab_agg("creatinine", "mean"),
            "wbc_max": lab_agg("wbc", "max"),
            "wbc_min": lab_agg("wbc", "min"),
            "hemoglobin_min": lab_agg("hemoglobin", "min"),
            "sodium_min": lab_agg("sodium", "min"),
            "sodium_max": lab_agg("sodium", "max"),
            "potassium_min": lab_agg("potassium", "min"),
            "potassium_max": lab_agg("potassium", "max"),
            "glucose_max": lab_agg("glucose", "max"),
            "glucose_mean": lab_agg("glucose", "mean"),
            "bun_max": lab_agg("bun", "max"),
            "lactate_max": lab_agg("lactate", "max"),
            "inr_max": lab_agg("inr", "max"),
            "bilirubin_max": lab_agg("bilirubin", "max"),
            "albumin_min": lab_agg("albumin", "min"),
            "troponin_max": lab_agg("troponin", "max"),
        }
        return pd.DataFrame([record])
    raise HTTPException(status_code=400, detail="No patient data provided")


@router.post(
    "",
    response_model=PredictionResponse,
    summary="Predict 30-Day Readmission Risk",
    description=(
        "Runs the ensemble ML pipeline and returns risk score, "
        "confidence interval, SHAP explanations, and recommended clinical actions."
    ),
)
async def predict_readmission(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    # user: dict = Depends(require_permission("read")),  # Enable in prod
) -> PredictionResponse:
    """Predict readmission risk for a patient."""
    try:
        engine = get_inference_engine()

        if request.patient_data:
            patient_df = _build_patient_df(request)
        else:
            # Demo mode: generate synthetic patient
            gen = SyntheticDataGenerator()
            payload = gen.generate_api_payload()
            from app.schemas.schemas import AdmissionCreate
            pd_data = AdmissionCreate(
                patient_id=uuid.uuid4(),
                admit_time=datetime.now(timezone.utc),
                icd_codes=payload["patient_info"].get("comorbidities", []),
            )
            request.patient_data = pd_data
            patient_df = _build_patient_df(request)

        result = engine.predict(
            patient_df,
            include_shap=request.include_shap,
        )

        prediction_id = uuid.uuid4()
        admission_id = (
            request.admission_id
            if request.admission_id
            else uuid.uuid4()
        )

        # Async audit log
        # background_tasks.add_task(
        #     audit_log, user.get("sub", "anon"), "predict", str(admission_id)
        # )

        features = [
            FeatureImportance(
                feature=f["feature"],
                shap_value=f["shap_value"],
                feature_value=f.get("feature_value"),
                direction=f["direction"],
                percentile=None,
            )
            for f in result["top_features"]
        ]

        return PredictionResponse(
            prediction_id=prediction_id,
            admission_id=admission_id,
            risk_score=result["risk_score"],
            risk_tier=result["risk_tier"],
            confidence_lower=result["confidence_lower"],
            confidence_upper=result["confidence_upper"],
            top_features=features,
            clinical_explanation=result["clinical_explanation"],
            model_version=result["model_version"],
            model_name=result["model_name"],
            predicted_at=datetime.now(timezone.utc),
            recommended_actions=result["recommended_actions"],
        )

    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction pipeline error: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=BatchPredictionResponse,
    summary="Batch Predict Readmission Risk",
)
async def batch_predict(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """Batch prediction for a cohort of patients (demo: returns synthetic results)."""
    gen = SyntheticDataGenerator()
    predictions = []
    engine = get_inference_engine()

    for _ in request.admission_ids:
        payload = gen.generate_api_payload()
        patient = payload["patient_info"]
        admission = payload["patient_data"]

        # Build minimal DataFrame
        record = {
            "age": patient.get("age", 65),
            "gender": patient.get("gender", "M"),
            "los_days": 3.0,
            "admission_type": "EMERGENCY",
            "icd_codes": patient.get("comorbidities", []),
            "procedure_codes": [],
        }
        df = pd.DataFrame([record])
        result = engine.predict(df, include_shap=False)

        predictions.append(PredictionResponse(
            prediction_id=uuid.uuid4(),
            admission_id=uuid.uuid4(),
            risk_score=result["risk_score"],
            risk_tier=result["risk_tier"],
            confidence_lower=result["confidence_lower"],
            confidence_upper=result["confidence_upper"],
            top_features=[],
            clinical_explanation=result["clinical_explanation"],
            model_version=result["model_version"],
            model_name=result["model_name"],
            predicted_at=datetime.now(timezone.utc),
            recommended_actions=result["recommended_actions"],
        ))

    high = sum(1 for p in predictions if p.risk_tier == "HIGH")
    medium = sum(1 for p in predictions if p.risk_tier == "MEDIUM")
    low = sum(1 for p in predictions if p.risk_tier == "LOW")

    return BatchPredictionResponse(
        predictions=predictions,
        total=len(predictions),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
    )


@router.get(
    "/demo",
    response_model=PredictionResponse,
    summary="Demo Prediction (No Auth Required)",
    description="Returns a prediction for a randomly generated synthetic patient. Useful for UI testing.",
)
async def demo_prediction() -> PredictionResponse:
    """Demo prediction endpoint for testing."""
    return await predict_readmission(
        PredictionRequest(model_name="ensemble", include_shap=True),
        BackgroundTasks(),
    )
