"""
ReadmitIQ — Database Layer
Async SQLAlchemy ORM with PostgreSQL.
"""

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

AsyncSessionFactory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


# ── Models ────────────────────────────────────────────────────────────────────

class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mrn = Column(String(64), unique=True, nullable=False, index=True)  # Medical Record Number
    age = Column(Integer)
    gender = Column(String(16))
    ethnicity = Column(String(64))
    primary_diagnosis_icd = Column(String(16))
    comorbidities = Column(JSON, default=list)
    insurance_type = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    admissions = relationship("Admission", back_populates="patient", lazy="selectin")


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    hadm_id = Column(String(32), unique=True, index=True)  # MIMIC-compatible
    admit_time = Column(DateTime(timezone=True))
    discharge_time = Column(DateTime(timezone=True))
    los_days = Column(Float)                  # Length of stay
    admission_type = Column(String(32))       # EMERGENCY, ELECTIVE, etc.
    admission_location = Column(String(64))
    discharge_location = Column(String(64))
    drg_code = Column(String(16))             # DRG classification
    icd_codes = Column(JSON, default=list)    # ICD-9/10 codes
    procedure_codes = Column(JSON, default=list)
    was_readmitted_30d = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="admissions")
    vitals = relationship("VitalSigns", back_populates="admission", lazy="selectin")
    labs = relationship("LabResult", back_populates="admission", lazy="selectin")
    predictions = relationship("PredictionResult", back_populates="admission")


class VitalSigns(Base):
    __tablename__ = "vital_signs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_id = Column(UUID(as_uuid=True), ForeignKey("admissions.id"), nullable=False, index=True)
    chart_time = Column(DateTime(timezone=True), nullable=False)
    heart_rate = Column(Float)
    systolic_bp = Column(Float)
    diastolic_bp = Column(Float)
    respiratory_rate = Column(Float)
    temperature = Column(Float)
    spo2 = Column(Float)
    gcs_total = Column(Integer)

    admission = relationship("Admission", back_populates="vitals")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_id = Column(UUID(as_uuid=True), ForeignKey("admissions.id"), nullable=False, index=True)
    chart_time = Column(DateTime(timezone=True), nullable=False)
    label = Column(String(128))              # e.g. "Creatinine", "WBC"
    value = Column(Float)
    unit = Column(String(32))
    flag = Column(String(16))               # normal / abnormal / critical

    admission = relationship("Admission", back_populates="labs")


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admission_id = Column(UUID(as_uuid=True), ForeignKey("admissions.id"), nullable=False, index=True)
    model_version = Column(String(32), nullable=False)
    risk_score = Column(Float, nullable=False)         # 0..1
    risk_tier = Column(String(16), nullable=False)     # LOW / MEDIUM / HIGH
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    shap_values = Column(JSON)                         # per-feature SHAP
    top_features = Column(JSON)                        # top-k features for UI
    clinical_explanation = Column(Text)                # LLM-generated text
    predicted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    model_name = Column(String(64))                    # ensemble / xgboost / etc.

    admission = relationship("Admission", back_populates="predictions")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(32), unique=True, nullable=False)
    model_type = Column(String(64))          # ensemble / xgboost / lgbm / lstm
    auc_roc = Column(Float)
    auc_pr = Column(Float)
    f1_score = Column(Float)
    brier_score = Column(Float)
    n_train_samples = Column(Integer)
    feature_names = Column(JSON)
    hyperparameters = Column(JSON)
    artifact_path = Column(String(256))
    is_production = Column(Boolean, default=False)
    trained_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(128))
    action = Column(String(64))
    resource = Column(String(128))
    detail = Column(Text)
    ip_address = Column(String(45))
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ── Session dependency ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
