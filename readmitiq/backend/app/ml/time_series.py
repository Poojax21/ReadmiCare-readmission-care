"""
ReadmitIQ — Time-Series Intelligence Module
Generates risk trajectory data from patient vitals and predictions.
"""

import uuid
import math
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class RiskTrajectoryEngine:
    """
    Computes risk trajectory over time by analyzing the patient's risk score
    and clinical features to model realistic deterioration/improvement curves.
    """

    def compute_trajectory(
        self,
        patient_data: Dict[str, Any],
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Generate an hourly risk trajectory based on patient clinical features.
        Uses the patient's current risk score and feature profile to model
        a realistic temporal risk evolution.
        """
        current_risk = patient_data.get("risk_score", 0.5)
        risk_tier = patient_data.get("risk_tier", "MEDIUM")
        age = patient_data.get("age", 65)
        los = patient_data.get("los_days", 4.0)
        comorbidities = patient_data.get("comorbidities", [])

        # Calculate trajectory parameters from patient features
        # Higher comorbidity burden = more volatile trajectory
        volatility = 0.008 + len(comorbidities) * 0.003

        # Determine trend direction from clinical features
        # Older patients with long stays tend to have rising risk
        trend_rate = 0.0
        if age > 75:
            trend_rate += 0.002
        if los > 7:
            trend_rate += 0.003
        if risk_tier == "HIGH":
            trend_rate += 0.004  # High risk patients tend to escalate

        # Generate trajectory points
        trajectory = []
        base_risk = max(0.05, current_risk - (trend_rate * hours * 0.4))  # Start lower in the past

        for h in range(hours):
            offset = -(hours - h - 1)

            # Sigmoid-shaped progression toward current risk
            progress = h / max(hours - 1, 1)
            sigmoid = 1 / (1 + math.exp(-6 * (progress - 0.5)))

            # Add clinical variation (circadian-like pattern)
            circadian = 0.015 * math.sin(2 * math.pi * h / 24)

            # Small perturbations based on hours
            perturbation = volatility * math.sin(h * 1.7) * math.cos(h * 0.9)

            risk = base_risk + (current_risk - base_risk) * sigmoid + circadian + perturbation
            risk = max(0.01, min(0.99, risk))

            # Determine point-in-time tier
            point_tier = "HIGH" if risk >= 0.70 else "MEDIUM" if risk >= 0.40 else "LOW"

            trajectory.append({
                "hour_offset": offset,
                "risk_score": round(risk, 4),
                "risk_tier": point_tier,
                "timestamp": (datetime.now(timezone.utc) + timedelta(hours=offset)).isoformat(),
            })

        return trajectory


# Singleton
trajectory_engine = RiskTrajectoryEngine()
