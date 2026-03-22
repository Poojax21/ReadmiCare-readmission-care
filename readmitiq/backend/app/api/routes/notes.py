"""
ReadmitIQ — Clinical Notes NLP Extraction API
Extracts structured clinical entities, risk signals, and severity indicators
from unstructured physician notes using rule-based NLP.
"""

import re
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────

class NotesExtractRequest(BaseModel):
    """Request to analyze clinical notes."""
    note_text: str = Field(
        ..., min_length=10, max_length=10000,
        description="Free-text clinical note to analyze",
    )
    include_severity: bool = Field(True, description="Include severity scoring")


class ExtractedEntity(BaseModel):
    """A single extracted clinical entity."""
    text: str
    category: str  # CONDITION, SYMPTOM, MEDICATION, VITAL_SIGN, LAB_RESULT, BEHAVIOR
    severity: Optional[str] = None  # CRITICAL, HIGH, MODERATE, LOW
    icd_hint: Optional[str] = None  # Suggested ICD-10 code prefix


class RiskSignal(BaseModel):
    """An identified risk signal from the note."""
    signal: str
    risk_category: str  # readmission_risk, mortality_risk, deterioration_risk
    evidence: str
    impact: str  # HIGH, MODERATE, LOW


class NotesExtractResponse(BaseModel):
    """Full NLP extraction result."""
    entities: List[ExtractedEntity]
    risk_signals: List[RiskSignal]
    summary: str
    overall_risk_modifier: str  # INCREASES, NEUTRAL, DECREASES
    readmission_flags_count: int


# ── Clinical NLP Patterns ─────────────────────────────────────────────
# Production-grade pattern matching for clinical terminology

CONDITION_PATTERNS: List[Dict] = [
    {"pattern": r"\b(heart failure|chf|hf)\b", "category": "CONDITION", "severity": "HIGH", "icd": "I50", "signal": "Heart failure — top readmission driver"},
    {"pattern": r"\b(atrial fibrillation|a\.?fib|afib)\b", "category": "CONDITION", "severity": "MODERATE", "icd": "I48", "signal": "Arrhythmia requiring anticoagulation management"},
    {"pattern": r"\b(copd|chronic obstructive)\b", "category": "CONDITION", "severity": "HIGH", "icd": "J44", "signal": "COPD exacerbation — high readmission risk"},
    {"pattern": r"\b(pneumonia)\b", "category": "CONDITION", "severity": "HIGH", "icd": "J18", "signal": "Active pneumonia requiring follow-up"},
    {"pattern": r"\b(diabetes|diabetic|dm\s?(type)?\s?(1|2|ii|i)?)\b", "category": "CONDITION", "severity": "MODERATE", "icd": "E11", "signal": "Diabetes management affects recovery trajectory"},
    {"pattern": r"\b(chronic kidney|ckd|renal (?:failure|insufficiency))\b", "category": "CONDITION", "severity": "HIGH", "icd": "N18", "signal": "Chronic kidney disease increases readmission risk"},
    {"pattern": r"\b(acute kidney|aki)\b", "category": "CONDITION", "severity": "CRITICAL", "icd": "N17", "signal": "Acute kidney injury — nephrology follow-up critical"},
    {"pattern": r"\b(sepsis|septic)\b", "category": "CONDITION", "severity": "CRITICAL", "icd": "A41", "signal": "Sepsis history — infection monitoring essential"},
    {"pattern": r"\b(hypertension|htn)\b", "category": "CONDITION", "severity": "LOW", "icd": "I10", "signal": "Hypertension — ensure BP management plan"},
    {"pattern": r"\b(stroke|cva|cerebrovascular)\b", "category": "CONDITION", "severity": "CRITICAL", "icd": "I63", "signal": "Stroke — neurology follow-up essential"},
    {"pattern": r"\b(cirrhosis|hepatic failure)\b", "category": "CONDITION", "severity": "CRITICAL", "icd": "K74", "signal": "Liver disease — complex medication adjustments needed"},
]

SYMPTOM_PATTERNS: List[Dict] = [
    {"pattern": r"\b(dyspnea|shortness of breath|sob)\b", "category": "SYMPTOM", "severity": "HIGH", "signal": "Respiratory distress"},
    {"pattern": r"\b(chest pain|angina)\b", "category": "SYMPTOM", "severity": "CRITICAL", "signal": "Chest pain — cardiac workup needed"},
    {"pattern": r"\b(tachycardia|rapid heart|elevated hr)\b", "category": "SYMPTOM", "severity": "HIGH", "signal": "Tachycardia — arrhythmia risk"},
    {"pattern": r"\b(hypotension|low blood pressure|low bp)\b", "category": "SYMPTOM", "severity": "HIGH", "signal": "Hypotension — hemodynamic instability"},
    {"pattern": r"\b(edema|swelling|fluid (?:overload|retention))\b", "category": "SYMPTOM", "severity": "MODERATE", "signal": "Fluid management issue"},
    {"pattern": r"\b(confusion|altered mental|delirium|ams)\b", "category": "SYMPTOM", "severity": "HIGH", "signal": "Altered mental status — delirium screening"},
    {"pattern": r"\b(fever|febrile|temperature\s*(?:>|above|elevated))\b", "category": "SYMPTOM", "severity": "MODERATE", "signal": "Fever — potential infection"},
    {"pattern": r"\b(nausea|vomiting|emesis)\b", "category": "SYMPTOM", "severity": "LOW", "signal": "GI symptoms — medication tolerance"},
    {"pattern": r"\b(fall|fallen|fell)\b", "category": "SYMPTOM", "severity": "MODERATE", "signal": "Fall risk — PT/OT assessment recommended"},
    {"pattern": r"\b(pain\s+(?:worse|worsening|increasing|uncontrolled))\b", "category": "SYMPTOM", "severity": "HIGH", "signal": "Uncontrolled pain — analgesic review"},
]

BEHAVIOR_PATTERNS: List[Dict] = [
    {"pattern": r"\b(non[\s-]?compli(?:ant|ance)|noncompliant|not (?:taking|adhering))\b", "category": "BEHAVIOR", "severity": "HIGH", "signal": "Medication non-adherence — primary readmission driver"},
    {"pattern": r"\b(missed (?:appointments?|follow[\s-]?ups?)|no[\s-]?show)\b", "category": "BEHAVIOR", "severity": "HIGH", "signal": "Missed follow-ups — engagement intervention needed"},
    {"pattern": r"\b(lives alone|social isolation|no support)\b", "category": "BEHAVIOR", "severity": "MODERATE", "signal": "Social isolation — home health or community support"},
    {"pattern": r"\b(homeless|unhoused|unstable housing)\b", "category": "BEHAVIOR", "severity": "CRITICAL", "signal": "Housing instability — social work referral critical"},
    {"pattern": r"\b(substance (?:abuse|use)|alcohol|drinking|drug use)\b", "category": "BEHAVIOR", "severity": "HIGH", "signal": "Substance use — specialized discharge planning"},
    {"pattern": r"\b(smoker|smoking|tobacco)\b", "category": "BEHAVIOR", "severity": "MODERATE", "signal": "Smoking — cessation counseling at discharge"},
    {"pattern": r"\b(poor (?:oral|nutrition|dietary)|malnourish)\b", "category": "BEHAVIOR", "severity": "MODERATE", "signal": "Nutritional deficit — dietitian referral"},
]


@router.post("/extract", response_model=NotesExtractResponse)
async def extract_risk_signals(request: NotesExtractRequest):
    """
    Extracts structured clinical entities and readmission risk signals
    from unstructured physician notes using clinical NLP patterns.
    """
    text = request.note_text
    text_lower = text.lower()

    entities: List[ExtractedEntity] = []
    risk_signals: List[RiskSignal] = []
    seen_signals = set()

    all_patterns = CONDITION_PATTERNS + SYMPTOM_PATTERNS + BEHAVIOR_PATTERNS

    for pattern_def in all_patterns:
        matches = re.finditer(pattern_def["pattern"], text_lower)
        for match in matches:
            matched_text = match.group(0).strip()

            entities.append(ExtractedEntity(
                text=matched_text,
                category=pattern_def["category"],
                severity=pattern_def.get("severity"),
                icd_hint=pattern_def.get("icd"),
            ))

            signal_key = pattern_def.get("signal", matched_text)
            if signal_key not in seen_signals:
                seen_signals.add(signal_key)
                severity = pattern_def.get("severity", "LOW")
                risk_signals.append(RiskSignal(
                    signal=signal_key,
                    risk_category="readmission_risk" if severity in ["CRITICAL", "HIGH"] else "deterioration_risk",
                    evidence=f"Found '{matched_text}' in clinical note",
                    impact=severity,
                ))

    # Determine overall modifier
    critical_count = sum(1 for s in risk_signals if s.impact in ["CRITICAL", "HIGH"])
    if critical_count >= 3:
        modifier = "INCREASES"
    elif critical_count >= 1:
        modifier = "INCREASES"
    elif len(risk_signals) == 0:
        modifier = "NEUTRAL"
    else:
        modifier = "NEUTRAL"

    # Build summary
    if not entities:
        summary = "No significant clinical risk signals identified in the provided note text."
    else:
        condition_count = sum(1 for e in entities if e.category == "CONDITION")
        symptom_count = sum(1 for e in entities if e.category == "SYMPTOM")
        behavior_count = sum(1 for e in entities if e.category == "BEHAVIOR")

        parts = []
        if condition_count: parts.append(f"{condition_count} condition(s)")
        if symptom_count: parts.append(f"{symptom_count} symptom(s)")
        if behavior_count: parts.append(f"{behavior_count} behavioral factor(s)")

        summary = (
            f"Extracted {', '.join(parts)} from the clinical note. "
            f"{critical_count} high/critical risk signals identified "
            f"that may impact 30-day readmission risk."
        )

    return NotesExtractResponse(
        entities=entities,
        risk_signals=risk_signals,
        summary=summary,
        overall_risk_modifier=modifier,
        readmission_flags_count=critical_count,
    )
