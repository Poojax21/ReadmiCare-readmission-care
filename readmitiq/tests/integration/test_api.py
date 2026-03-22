"""
ReadmitIQ — Integration Tests
API endpoint testing via FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:

    def test_health_check(self):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ReadmitIQ API"

    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "ReadmitIQ" in data["service"]


class TestPredictionEndpoints:

    def test_demo_prediction(self):
        r = client.get("/api/v1/predict/demo")
        assert r.status_code == 200
        data = r.json()
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"] <= 1.0
        assert data["risk_tier"] in ("HIGH", "MEDIUM", "LOW")
        assert "clinical_explanation" in data
        assert len(data["recommended_actions"]) > 0

    def test_predict_with_payload(self):
        payload = {
            "patient_data": {
                "patient_id": "00000000-0000-0000-0000-000000000001",
                "admit_time": "2024-01-15T08:30:00Z",
                "admission_type": "EMERGENCY",
                "icd_codes": ["I50.9", "E11.65"],
                "procedure_codes": [],
                "vitals": [
                    {
                        "chart_time": "2024-01-15T10:00:00Z",
                        "heart_rate": 105,
                        "systolic_bp": 95,
                        "diastolic_bp": 62,
                        "respiratory_rate": 24,
                        "temperature": 38.8,
                        "spo2": 90,
                        "gcs_total": 14,
                    }
                ],
                "labs": [
                    {"chart_time": "2024-01-15T09:00:00Z", "label": "Creatinine", "value": 2.4, "unit": "mg/dL"},
                    {"chart_time": "2024-01-15T09:00:00Z", "label": "Albumin", "value": 2.5, "unit": "g/dL"},
                ],
            },
            "model_name": "ensemble",
            "include_shap": True,
        }
        r = client.post("/api/v1/predict", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "risk_score" in data
        assert "confidence_lower" in data
        assert "confidence_upper" in data
        assert data["confidence_lower"] <= data["risk_score"] <= data["confidence_upper"]

    def test_prediction_response_schema(self):
        r = client.get("/api/v1/predict/demo")
        data = r.json()
        required_fields = [
            "prediction_id", "admission_id", "risk_score", "risk_tier",
            "confidence_lower", "confidence_upper", "clinical_explanation",
            "recommended_actions", "model_version", "model_name", "predicted_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


class TestPatientEndpoints:

    def test_list_patients(self):
        r = client.get("/api/v1/patients")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Should return demo patients
        assert len(data) >= 10

    def test_list_patients_high_risk_filter(self):
        r = client.get("/api/v1/patients?risk_tier=HIGH")
        assert r.status_code == 200
        data = r.json()
        for p in data:
            assert p["risk_tier"] == "HIGH"

    def test_list_patients_limit(self):
        r = client.get("/api/v1/patients?limit=5")
        assert r.status_code == 200
        data = r.json()
        assert len(data) <= 5

    def test_dashboard_stats(self):
        r = client.get("/api/v1/patients/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_active_admissions" in data
        assert "high_risk_count" in data
        assert "avg_risk_score" in data
        assert data["total_active_admissions"] >= 0

    def test_heatmap_data(self):
        r = client.get("/api/v1/patients/heatmap?limit=20")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            p = data[0]
            assert "risk_score" in p
            assert "risk_tier" in p
            assert "mrn" in p

    def test_patient_not_found(self):
        r = client.get("/api/v1/patients/nonexistent-id-123")
        assert r.status_code == 404


class TestCohortEndpoints:

    def test_analyze_cohort_all(self):
        r = client.post("/api/v1/cohorts", json={})
        assert r.status_code == 200
        data = r.json()
        assert "total_patients" in data
        assert "high_risk" in data
        assert data["total_patients"] >= 0

    def test_analyze_cohort_high_risk_filter(self):
        r = client.post("/api/v1/cohorts", json={"risk_tier": ["HIGH"]})
        assert r.status_code == 200
        data = r.json()
        assert data["medium_risk"] == 0
        assert data["low_risk"] == 0

    def test_analyze_cohort_age_filter(self):
        r = client.post("/api/v1/cohorts", json={"age_min": 65, "age_max": 85})
        assert r.status_code == 200
        data = r.json()
        assert "avg_age" in data
        if data["total_patients"] > 0:
            assert 60 <= data["avg_age"] <= 90


class TestRetrainEndpoints:

    def test_trigger_retrain(self):
        r = client.post("/api/v1/retrain", json={
            "dataset_source": "synthetic",
            "model_types": ["xgboost"],
            "n_optuna_trials": 5,
        })
        assert r.status_code == 200
        data = r.json()
        assert "task_id" in data
        assert data["status"] in ("PENDING", "RUNNING")

    def test_retrain_status_not_found(self):
        r = client.get("/api/v1/retrain/nonexistent-task")
        assert r.status_code == 404

    def test_list_retrain_tasks(self):
        r = client.get("/api/v1/retrain")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestOpenAPISchema:

    def test_openapi_schema_accessible(self):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert "components" in schema

    def test_docs_accessible(self):
        r = client.get("/api/docs")
        assert r.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
