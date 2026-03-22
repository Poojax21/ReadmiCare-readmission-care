"""
ReadmitIQ — WebSocket Routes
Real-time patient risk alerts and live dashboard updates.
"""

import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)
        logger.info(f"WebSocket connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)
        logger.info(f"WebSocket disconnected. Total: {len(self.active)}")

    async def broadcast(self, message: dict) -> None:
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.active -= dead


manager = ConnectionManager()


async def _alert_generator(ws: WebSocket) -> None:
    """Stream simulated real-time alerts every few seconds."""
    RISK_TIERS = ["HIGH", "HIGH", "MEDIUM", "LOW", "MEDIUM"]
    DIAGNOSES = ["I50.9", "J44.1", "N17.9", "A41.9", "E11.65", "I21.9"]
    ACTIONS = [
        "Schedule 7-day follow-up",
        "Medication reconciliation required",
        "Home health assessment ordered",
        "Social work consult needed",
        "Transitional care enrolled",
    ]

    while True:
        await asyncio.sleep(random.uniform(4, 10))

        tier = random.choice(RISK_TIERS)
        score = (
            random.uniform(0.70, 0.96) if tier == "HIGH"
            else random.uniform(0.40, 0.69) if tier == "MEDIUM"
            else random.uniform(0.05, 0.39)
        )

        alert = {
            "type": "patient_alert",
            "payload": {
                "alert_id": str(uuid.uuid4()),
                "patient_mrn": f"MRN{random.randint(100000, 999999)}",
                "risk_score": round(score, 3),
                "risk_tier": tier,
                "primary_diagnosis": random.choice(DIAGNOSES),
                "recommended_action": random.choice(ACTIONS),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "priority": "CRITICAL" if score > 0.85 else ("WARN" if score > 0.6 else "INFO"),
                "ai_explanation": f"AI Copilot notes escalating risk trajectory based on recent {random.choice(DIAGNOSES)} indicators."
            },
        }

        try:
            await ws.send_json(alert)
        except WebSocketDisconnect:
            break


@router.websocket("/alerts")
async def alerts_ws(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time high-risk patient alerts.
    Streams new alerts as patients are assessed.
    """
    await manager.connect(ws)
    try:
        # Send initial connection confirmation
        await ws.send_json({
            "type": "connected",
            "payload": {
                "message": "ReadmitIQ Alert Stream connected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        })
        # Start streaming alerts
        await _alert_generator(ws)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


@router.websocket("/dashboard")
async def dashboard_ws(ws: WebSocket) -> None:
    """
    WebSocket endpoint for live dashboard metric updates.
    Streams aggregated stats every 30 seconds.
    """
    await manager.connect(ws)
    try:
        while True:
            await asyncio.sleep(30)
            stats = {
                "type": "dashboard_update",
                "payload": {
                    "high_risk_count": random.randint(8, 20),
                    "medium_risk_count": random.randint(25, 45),
                    "low_risk_count": random.randint(30, 50),
                    "avg_risk_score": round(random.uniform(0.25, 0.45), 3),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await ws.send_json(stats)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
