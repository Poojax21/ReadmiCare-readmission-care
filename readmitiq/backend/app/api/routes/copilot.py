"""
ReadmitIQ — AI Copilot API Endpoints
Provides conversational clinical decision support by combining
real patient data with ML model explanations.
"""

import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_rag import reasoning_engine

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────

class CopilotQueryRequest(BaseModel):
    """Request payload for AI Copilot queries."""
    patient_id: uuid.UUID = Field(..., description="Patient UUID to query about")
    query: str = Field(..., min_length=3, max_length=500, description="Clinical question")


class RiskContext(BaseModel):
    """Contextual risk information returned with copilot response."""
    score: float
    tier: str
    top_driver: str


class CopilotQueryResponse(BaseModel):
    """Response from the AI Copilot."""
    answer: str
    clinical_references: List[str]
    matched_conditions: List[str]
    risk_context: RiskContext


class CopilotHistoryItem(BaseModel):
    """Single conversation turn."""
    role: str  # "user" or "assistant"
    content: str


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/query", response_model=CopilotQueryResponse)
async def copilot_chat(request: CopilotQueryRequest):
    """
    AI Doctor Copilot — answers clinical questions about a specific patient.
    Combines real patient EHR data with SHAP model explanations and
    evidence-based clinical guidelines.
    """
    # Fetch real patient data from the demo store
    from app.api.routes.patients import _init_demo, _demo_patients
    _init_demo()

    patient = next(
        (p for p in _demo_patients if p["id"] == str(request.patient_id)),
        None,
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    risk_score = patient.get("risk_score", 0.5)
    risk_tier = patient.get("risk_tier", "MEDIUM")
    shap_features = patient.get("top_features", [])

    try:
        response = await reasoning_engine.generate_response(
            query=request.query,
            patient_data=patient,
            shap_features=shap_features,
            risk_score=risk_score,
            risk_tier=risk_tier,
        )

        return CopilotQueryResponse(
            answer=response["answer"],
            clinical_references=response["clinical_references"],
            matched_conditions=response["matched_conditions"],
            risk_context=RiskContext(**response["risk_context"]),
        )
    except Exception as e:
        logger.error(f"Copilot error for patient {request.patient_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal copilot error")
