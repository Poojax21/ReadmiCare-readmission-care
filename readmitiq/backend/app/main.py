"""
ReadmitIQ — Intelligent Hospital Readmission Prediction Platform
FastAPI Backend — Main Application Entry Point
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import predict, patients, cohorts, retrain, websocket, copilot, simulation, notes, financials
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import init_db

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("🏥 ReadmitIQ starting up...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("🔒 ReadmitIQ shutting down...")


app = FastAPI(
    title="ReadmitIQ API",
    description=(
        "Production-grade hospital readmission prediction platform. "
        "Provides real-time risk scoring, explainable AI insights, "
        "and clinical decision support."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(predict.router,   prefix="/api/v1/predict",  tags=["Prediction"])
app.include_router(patients.router,  prefix="/api/v1/patients", tags=["Patients"])
app.include_router(cohorts.router,   prefix="/api/v1/cohorts",  tags=["Cohorts"])
app.include_router(retrain.router,   prefix="/api/v1/retrain",  tags=["Model Training"])
app.include_router(copilot.router,   prefix="/api/v1/copilot",  tags=["AI Copilot"])
app.include_router(simulation.router,prefix="/api/v1/simulation",tags=["Simulation Base"])
app.include_router(notes.router,     prefix="/api/v1/notes",    tags=["Clinical Notes NLP"])
app.include_router(financials.router,prefix="/api/v1/financials",tags=["ROI & Cost Impact"])
app.include_router(websocket.router, prefix="/ws",              tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "ReadmitIQ API", "version": "1.0.0"})


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "ReadmitIQ",
        "tagline": "Intelligent Hospital Readmission Prediction",
        "docs": "/api/docs",
    }
