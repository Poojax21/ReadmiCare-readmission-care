"""
ReadmitIQ — API Schemas
Pydantic v2 models for request/response validation and serialization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Base ──────────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


# ── Patient ───────────────────────────────────────────────────────────────────

class VitalSnapshot(BaseModel):
    chart_time: datetime
    heart_rate: Optional[float] = Field(None, ge=0, le=300, description="Heart rate (0-300 bpm)")
    systolic_bp: Optional[float] = Field(None, ge=0, le=300, description="Systolic blood pressure (0-300 mmHg)")
    diastolic_bp: Optional[float] = Field(None, ge=0, le=200, description="Diastolic blood pressure (0-200 mmHg)")
    respiratory_rate: Optional[float] = Field(None, ge=0, le=60, description="Respiratory rate (0-60 breaths/min)")
    temperature: Optional[float] = Field(None, ge=30, le=45, description="Body temperature (30-45°C)")
    spo2: Optional[float] = Field(None, ge=0, le=100, description="Oxygen saturation (0-100%)")
    gcs_total: Optional[int] = Field(None, ge=3, le=15, description="Glasgow Coma Scale (3-15)")

    @field_validator('heart_rate')
    @classmethod
    def validate_heart_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 20 or v > 250):
            raise ValueError('Heart rate must be between 20-250 bpm')
        return v

    @field_validator('systolic_bp')
    @classmethod
    def validate_sbp(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 50 or v > 250):
            raise ValueError('Systolic BP must be between 50-250 mmHg')
        return v

    @field_validator('spo2')
    @classmethod
    def validate_spo2(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 50 or v > 100):
            raise ValueError('SpO2 must be between 50-100%')
        return v


class LabSnapshot(BaseModel):
    chart_time: datetime
    label: str = Field(..., min_length=1, max_length=100, description="Lab test name")
    value: float = Field(..., description="Lab test value")
    unit: Optional[str] = Field(None, max_length=20, description="Unit of measurement")
    flag: Optional[str] = Field(None, max_length=10, description="Abnormal flag (H/L/N)")

    @field_validator('value')
    @classmethod
    def validate_value(cls, v: float) -> float:
        if not (-10000 <= v <= 10000):
            raise ValueError('Lab value must be between -10000 and 10000')
        return v

    @field_validator('flag')
    @classmethod
    def validate_flag(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in ['H', 'L', 'N', 'HH', 'LL', 'ANL']:
            raise ValueError('Lab flag must be H (high), L (low), N (normal), HH, LL, or ANL')
        return v.upper() if v else v


class PatientCreate(BaseModel):
    mrn: str = Field(..., min_length=1, max_length=64, description="Medical Record Number")
    first_name: Optional[str] = Field(None, max_length=64, description="Patient first name")
    last_name: Optional[str] = Field(None, max_length=64, description="Patient last name")
    age: int = Field(..., ge=0, le=120, description="Patient age in years (0-120)")
    gender: str = Field(..., pattern="^(M|F|Other|Unknown)$", description="Patient gender: M, F, Other, or Unknown")
    ethnicity: Optional[str] = Field(None, max_length=64, description="Patient ethnicity")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (YYYY-MM-DD)")
    phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    primary_diagnosis_icd: Optional[str] = Field(None, max_length=16, description="ICD-10 diagnosis code")
    primary_diagnosis_name: Optional[str] = Field(None, max_length=128, description="Diagnosis description")
    comorbidities: List[str] = Field(default_factory=list, description="List of comorbidities")
    insurance_type: Optional[str] = Field(None, max_length=64, description="Insurance type")
    attending_physician: Optional[str] = Field(None, max_length=128, description="Attending physician name")
    ward: Optional[str] = Field(None, max_length=64, description="Current ward/unit")

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 0 or v > 120:
            raise ValueError('Age must be between 0 and 120 years')
        return v

    @field_validator('mrn')
    @classmethod
    def validate_mrn(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Medical Record Number cannot be empty')
        return v.strip()


class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mrn: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    ethnicity: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None
    primary_diagnosis_icd: Optional[str] = None
    primary_diagnosis_name: Optional[str] = None
    comorbidities: List[str] = []
    insurance_type: Optional[str] = None
    attending_physician: Optional[str] = None
    ward: Optional[str] = None
    latest_risk_score: Optional[float] = None
    risk_tier: Optional[str] = None


# ── Admission ─────────────────────────────────────────────────────────────────

class AdmissionCreate(BaseModel):
    patient_id: uuid.UUID
    hadm_id: Optional[str] = None
    admit_time: datetime
    discharge_time: Optional[datetime] = None
    admission_type: Optional[str] = None
    admission_location: Optional[str] = None
    drg_code: Optional[str] = None
    icd_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    vitals: List[VitalSnapshot] = Field(default_factory=list)
    labs: List[LabSnapshot] = Field(default_factory=list)


# ── Prediction ────────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    """Payload for /predict endpoint."""
    admission_id: Optional[uuid.UUID] = Field(None, description="Existing admission ID")
    patient_data: Optional[AdmissionCreate] = Field(None, description="Inline patient data")
    model_name: str = Field("ensemble", description="Model: ensemble, xgboost, lgbm, or lstm")
    include_shap: bool = Field(True, description="Include SHAP explanations")
    include_lime: bool = Field(False, description="Include LIME explanations")
    include_explanation: bool = Field(True, description="Include clinical explanation")

    @field_validator('model_name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        valid_models = ['ensemble', 'xgboost', 'lgbm', 'lstm', 'logistic']
        if v not in valid_models:
            raise ValueError(f'model_name must be one of: {valid_models}')
        return v


class FeatureImportance(BaseModel):
    feature: str
    shap_value: float
    feature_value: Optional[float] = None
    direction: str  # "increases_risk" | "decreases_risk"
    percentile: Optional[float] = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prediction_id: uuid.UUID
    admission_id: uuid.UUID
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str                             # LOW / MEDIUM / HIGH
    confidence_lower: float
    confidence_upper: float
    top_features: List[FeatureImportance]
    clinical_explanation: str
    model_version: str
    model_name: str
    predicted_at: datetime
    recommended_actions: List[str]


class BatchPredictionRequest(BaseModel):
    admission_ids: List[uuid.UUID]
    model_name: str = "ensemble"
    include_shap: bool = True


class BatchPredictionResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


# ── Cohort ────────────────────────────────────────────────────────────────────

class CohortFilter(BaseModel):
    risk_tier: Optional[List[str]] = Field(None, description="Risk tiers: LOW, MEDIUM, HIGH")
    age_min: Optional[int] = Field(None, ge=0, le=120, description="Minimum age (0-120)")
    age_max: Optional[int] = Field(None, ge=0, le=120, description="Maximum age (0-120)")
    admission_type: Optional[List[str]] = Field(None, description="Admission types: EMERGENCY, ELECTIVE, URGENT")
    icd_prefix: Optional[str] = Field(None, max_length=10, description="ICD code prefix filter")
    los_min: Optional[float] = Field(None, ge=0, le=365, description="Minimum length of stay (days)")
    los_max: Optional[float] = Field(None, ge=0, le=365, description="Maximum length of stay (days)")
    date_from: Optional[datetime] = Field(None, description="Filter admissions from this date")
    date_to: Optional[datetime] = Field(None, description="Filter admissions until this date")

    @field_validator('age_min', 'age_max')
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 120):
            raise ValueError('Age must be between 0 and 120 years')
        return v

    @field_validator('los_min', 'los_max')
    @classmethod
    def validate_los(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 365):
            raise ValueError('Length of stay must be between 0 and 365 days')
        return v


class CohortSummary(BaseModel):
    total_patients: int
    high_risk: int
    medium_risk: int
    low_risk: int
    avg_risk_score: float
    avg_age: float
    avg_los: float
    top_diagnoses: List[Dict[str, Any]]
    readmission_rate_actual: Optional[float] = None


# ── Retraining ────────────────────────────────────────────────────────────────

class RetrainRequest(BaseModel):
    dataset_source: str = "database"           # "database" | "upload" | "synthetic"
    model_types: List[str] = Field(
        default=["xgboost", "lgbm", "logistic", "lstm"],
    )
    n_optuna_trials: int = Field(default=30, ge=5, le=200)
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    use_smote: bool = True
    target_metric: str = "roc_auc"


class RetrainStatus(BaseModel):
    task_id: str
    status: str   # PENDING / RUNNING / COMPLETED / FAILED
    progress: int = 0
    current_step: str = ""
    metrics: Optional[Dict[str, float]] = None
    error: Optional[str] = None


# ── Risk Dashboard ─────────────────────────────────────────────────────────────

class RiskHeatmapPoint(BaseModel):
    patient_id: uuid.UUID
    mrn: str
    age: int
    risk_score: float
    risk_tier: str
    primary_diagnosis: Optional[str]
    los_days: Optional[float]
    top_risk_factor: Optional[str]


class DashboardStats(BaseModel):
    total_active_admissions: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    avg_risk_score: float
    alerts_today: int
    model_accuracy: float
    last_updated: datetime
