"""
ReadmitIQ — Clinical Intervention Engine
Recommends personalized clinical interventions based on risk score,
top risk factors (SHAP), and patient clinical context.
"""

from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class ClinicalInterventionEngine:
    """
    Expert-system-like engine to map risk patterns to clinical actions.
    Moves the platform from analytics only to clinical decision support.
    """

    # ── Diagnosis-Specific Interventions ───────────────────────────────────────
    DIAGNOSIS_INTERVENTIONS = {
        "I50": [  # Heart Failure (CHF)
            "Schedule cardiologist follow-up within 3 days",
            "Daily weight monitoring (notify if >2lbs/day gain)",
            "Strict fluid restriction and low-sodium diet review",
            "Ensure patient has a 'Red Flag' symptoms list",
            "Home Health Care for weight/medication titration",
        ],
        "I21": [  # Acute MI
            "Early post-discharge cardiac rehabilitation enrollment",
            "Statist/Antiplatelet therapy adherence check",
            "Beta-blocker dose titration schedule",
            "Smoking cessation counseling if applicable",
        ],
        "J44": [  # COPD
            "Pulmonary rehabilitation referral",
            "Inhaler technique verification",
            "Home oxygen therapy assessment",
            "Pneumococcal/Influenza vaccination check",
        ],
        "N17": [  # AKI
            "Nephrology follow-up within 7 days",
            "Monitor serum creatinine and electrolytes daily for 3 days",
            "Avoid nephrotoxic drugs (NSAIDs, etc.)",
            "Strict intake/output monitoring",
        ],
        "E11": [  # Type 2 DM
            "Diabetes educator consultation before discharge",
            "Home glucose monitoring log review",
            "Podiatry referral for diabetic foot exam",
            "Medication titration (insulin/non-insulin)",
        ],
        "A41": [  # Sepsis
            "Post-sepsis syndrome screening program",
            "Infection source control follow-up",
            "PCP follow-up within 72 hours",
        ]
    }

    # ── Risk-Factor Specific Interventions (SHAP-driven) ───────────────────────
    FACTOR_INTERVENTIONS = {
        "aki_risk": [
            "Monitor creatinine daily for the first 48h post-discharge",
            "Review medication list for nephrotoxins",
        ],
        "hypoalbuminemia": [
            "Nutritional consultation for high-protein supplementation",
            "Assess for wound healing barriers",
        ],
        "hypoxia": [
            "Continuous pulse oximetry monitoring for first night",
            "Assess need for home oxygen",
        ],
        "charlson_index": [
            "Transitional Care Management (TCM) nurse assignment",
            "Comprehensive geriatric assessment",
        ],
        "los_days": [
            "Social worker consult for home environment safety",
            "Functional mobility assessment by physical therapy",
        ],
        "polypharmacy": [
            "Pharmacist-led medication reconciliation",
            "Simplify medication schedule to improve adherence",
        ],
        "shock_index": [
            "Extended observation for hemodynamic stability",
            "Close BP monitoring post-discharge",
        ]
    }

    def recommend_interventions(
        self,
        risk_score: float,
        top_features: List[Dict],
        patient_context: Dict,
    ) -> List[str]:
        """
        Synthesize personalized recommendations based on all available data.
        """
        interventions = set()

        # ── 1. Tier-Based Baseline ──────────────────────────────────────────────
        if risk_score >= 0.70:
            interventions.add("Schedule follow-up within 7 days of discharge")
            interventions.add("Consider transitional care management (TCM) program enrollment")
            interventions.add("Medication reconciliation before discharge")
        elif risk_score >= 0.40:
            interventions.add("Schedule follow-up within 14 days of discharge")
            interventions.add("Confirm patient has primary care physician")
        else:
            interventions.add("Standard discharge planning protocol")
            interventions.add("Ensure follow-up appointment is confirmed")

        # ── 2. Diagnosis-Specific logic ──────────────────────────────────────────
        icd_codes = patient_context.get("icd_codes", [])
        if not isinstance(icd_codes, list):
            icd_codes = []
            
        # Also check primary diagnosis
        primary_icd = patient_context.get("primary_diagnosis_icd", "")
        codes_to_check = [primary_icd] + icd_codes
        
        for code in codes_to_check:
            prefix = str(code)[:3]
            if prefix in self.DIAGNOSIS_INTERVENTIONS:
                for action in self.DIAGNOSIS_INTERVENTIONS[prefix]:
                    interventions.add(action)

        # ── 3. SHAP Feature-Driven logic ─────────────────────────────────────────
        # Focus on top 3 most influential risk-increasing factors
        pos_features = [f for f in top_features if f.get("direction") == "increases_risk"][:3]
        for f in pos_features:
            feat_name = f.get("feature")
            if feat_name in self.FACTOR_INTERVENTIONS:
                for action in self.FACTOR_INTERVENTIONS[feat_name]:
                    interventions.add(action)

        # ── 4. Age/Co-morbidity logic ───────────────────────────────────────────
        age = patient_context.get("age", 0)
        if age > 80 and risk_score > 0.5:
            interventions.add("Assess live-at-home safety and social support")
            interventions.add("Home safety evaluation by Occupational Therapy")

        # Convert back to sorted list and limit total count
        result = list(interventions)
        
        # Priority sort: ensure most specific ones are first
        # (Heuristic: diagnosis specific first, then factor specific, then tier)
        # For now, let's just sort alphabetically to keep it stable
        result.sort()
        
        # Cap at 6 interventions to avoid overwhelming clinicians
        return result[:6]

    def get_pitch_line(self) -> str:
        return "We don’t just predict risk — we recommend personalized interventions."
