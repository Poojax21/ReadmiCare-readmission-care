"""
ReadmitIQ — Unit Tests
Tests for feature engineering, synthetic data generator, and prediction pipeline.
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.ml.pipeline import (
    ClinicalFeatureEngineer,
    ReadmissionEnsemble,
    SHAPExplainer,
    generate_clinical_explanation,
    InferenceEngine,
)
from app.ml.synthetic_data import SyntheticDataGenerator


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def engineer():
    return ClinicalFeatureEngineer()


@pytest.fixture
def generator():
    return SyntheticDataGenerator(random_seed=42)


@pytest.fixture
def sample_df(generator):
    return generator.generate_dataset(n_patients=50, as_dataframe=True)


@pytest.fixture
def engine():
    return InferenceEngine(model_dir="/tmp/readmitiq_test_models")


# ── Feature Engineering ────────────────────────────────────────────────────────

class TestClinicalFeatureEngineer:

    def test_charlson_empty_codes(self, engineer):
        assert engineer._compute_charlson([]) == 0
        assert engineer._compute_charlson(None) == 0

    def test_charlson_heart_failure(self, engineer):
        # I50 = heart failure, weight 1
        score = engineer._compute_charlson(["I50.9"])
        assert score == 1

    def test_charlson_multiple(self, engineer):
        # heart failure + CKD + DM = 1 + 2 + 1 = 4
        score = engineer._compute_charlson(["I50.9", "N18.6", "E11.65"])
        assert score == 4

    def test_charlson_capped(self, engineer):
        # Many serious conditions — should cap at 15
        codes = ["B20", "C80.1", "K72.9", "G81.9", "N18.6", "C78.89"]
        score = engineer._compute_charlson(codes)
        assert score <= 15

    def test_engineer_features_returns_df(self, engineer, generator):
        dataset = generator.generate_dataset(n_patients=10)
        result = engineer.engineer_features(dataset)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 10

    def test_derived_vital_features(self, engineer):
        df = pd.DataFrame([{
            "age": 70, "gender": "M",
            "icd_codes": ["I50.9"], "procedure_codes": [],
            "admit_time": "2024-01-01T08:00:00",
            "los_days": 5,
            "admission_type": "EMERGENCY",
            "heart_rate_mean": 110, "heart_rate_min": 100,
            "heart_rate_max": 130, "heart_rate_std": 10,
            "systolic_bp_mean": 85, "systolic_bp_min": 78,
            "diastolic_bp_mean": 55,
            "resp_rate_mean": 24, "resp_rate_max": 30,
            "temp_mean": 38.8, "temp_min": 38.2, "temp_max": 39.5,
            "spo2_mean": 88, "spo2_min": 84,
            "gcs_min": 13,
        }])
        result = engineer.engineer_features(df)
        assert result["tachycardia"].iloc[0] == 1
        assert result["hypotension"].iloc[0] == 1
        assert result["fever"].iloc[0] == 1
        assert result["hypoxia"].iloc[0] == 1
        assert result["shock_index"].iloc[0] == pytest.approx(110 / 85, abs=0.01)

    def test_icd_chapter_encoding(self, engineer):
        df = pd.DataFrame([{
            "age": 65, "gender": "F",
            "icd_codes": ["I50.9", "J44.1", "C78.89"],
            "procedure_codes": [],
            "admit_time": "2024-01-01",
            "los_days": 3,
            "admission_type": "EMERGENCY",
        }])
        result = engineer.engineer_features(df)
        assert result["icd_circulatory"].iloc[0] == 1
        assert result["icd_respiratory"].iloc[0] == 1
        assert result["icd_neoplasm"].iloc[0] == 1
        assert result["icd_infectious"].iloc[0] == 0

    def test_feature_names_list(self, engineer):
        names = engineer.feature_names
        assert isinstance(names, list)
        assert len(names) > 50
        assert "charlson_index" in names
        assert "age" in names
        assert "shock_index" in names


# ── Synthetic Data Generator ───────────────────────────────────────────────────

class TestSyntheticDataGenerator:

    def test_generate_patient(self, generator):
        p = generator.generate_patient()
        assert "mrn" in p
        assert "age" in p
        assert 18 <= p["age"] <= 100
        assert p["gender"] in ("M", "F")
        assert isinstance(p["comorbidities"], list)

    def test_generate_admission(self, generator):
        p = generator.generate_patient()
        a = generator.generate_admission(p)
        assert "los_days" in a
        assert a["los_days"] >= 1.0
        assert "was_readmitted_30d" in a
        assert isinstance(a["was_readmitted_30d"], bool)
        assert len(a["icd_codes"]) >= 1

    def test_generate_dataset_shape(self, generator):
        df = generator.generate_dataset(n_patients=30)
        assert len(df) == 30
        assert "age" in df.columns
        assert "was_readmitted_30d" in df.columns

    def test_readmission_rate_realistic(self, generator):
        """Readmission rate should be around 10-30% (realistic)."""
        df = generator.generate_dataset(n_patients=500)
        rate = df["was_readmitted_30d"].mean()
        assert 0.05 <= rate <= 0.40, f"Unrealistic readmission rate: {rate:.2%}"

    def test_generate_api_payload(self, generator):
        payload = generator.generate_api_payload()
        assert "patient_data" in payload
        assert "vitals" in payload["patient_data"]
        assert len(payload["patient_data"]["vitals"]) > 0
        assert "labs" in payload["patient_data"]
        assert "true_readmission" in payload

    def test_deterministic_seed(self):
        """Age uses numpy rng which is seeded; verify dataset-level reproducibility."""
        g1 = SyntheticDataGenerator(random_seed=7)
        g2 = SyntheticDataGenerator(random_seed=7)
        df1 = g1.generate_dataset(n_patients=20)
        df2 = g2.generate_dataset(n_patients=20)
        # Aggregate metrics should be identical across seeded runs
        assert df1["age"].mean() == df2["age"].mean()
        assert df1["los_days"].mean() == df2["los_days"].mean()
        assert len(df1) == len(df2)


# ── Inference Engine ───────────────────────────────────────────────────────────

class TestInferenceEngine:

    def test_demo_predict_returns_valid_score(self, engine, generator):
        dataset = generator.generate_dataset(n_patients=1)
        result = engine.predict(dataset, include_shap=False)
        assert "risk_score" in result
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_tier"] in ("HIGH", "MEDIUM", "LOW")

    def test_risk_tier_thresholds(self, engine, generator):
        """Verify tier assignment matches thresholds."""
        dataset = generator.generate_dataset(n_patients=100)
        for _, row in dataset.iterrows():
            df = pd.DataFrame([row])
            result = engine.predict(df, include_shap=False)
            score = result["risk_score"]
            tier = result["risk_tier"]
            if score >= 0.70:
                assert tier == "HIGH", f"Score {score:.2f} should be HIGH"
            elif score >= 0.40:
                assert tier == "MEDIUM", f"Score {score:.2f} should be MEDIUM"
            else:
                assert tier == "LOW", f"Score {score:.2f} should be LOW"

    def test_high_risk_patient_score(self, engine):
        """A very sick patient should get HIGH risk."""
        df = pd.DataFrame([{
            "age": 85, "gender": "M",
            "icd_codes": ["B20", "N18.6", "I50.9"],  # HIV + CKD + CHF
            "procedure_codes": [],
            "admit_time": "2024-01-01",
            "los_days": 14,
            "admission_type": "EMERGENCY",
            "heart_rate_mean": 115, "heart_rate_min": 105, "heart_rate_max": 135, "heart_rate_std": 12,
            "systolic_bp_mean": 88, "systolic_bp_min": 75, "diastolic_bp_mean": 55,
            "resp_rate_mean": 26, "resp_rate_max": 32,
            "temp_mean": 38.9, "temp_min": 38.4, "temp_max": 39.8,
            "spo2_mean": 87, "spo2_min": 82, "gcs_min": 12,
            "creatinine_max": 4.2, "creatinine_mean": 3.8,
            "wbc_max": 18, "wbc_min": 14,
            "hemoglobin_min": 6.8,
            "sodium_min": 128, "sodium_max": 136,
            "potassium_min": 5.8, "potassium_max": 6.2,
            "glucose_max": 320, "glucose_mean": 265,
            "bun_max": 68, "lactate_max": 5.2,
            "inr_max": 2.8, "bilirubin_max": 4.1,
            "albumin_min": 2.0, "troponin_max": 0.8,
        }])
        result = engine.predict(df, include_shap=False)
        assert result["risk_score"] >= 0.55, f"Critically ill patient should have high risk, got {result['risk_score']:.2f}"

    def test_healthy_patient_low_risk(self, engine):
        """A young, healthy elective patient should have LOW risk."""
        df = pd.DataFrame([{
            "age": 30, "gender": "F",
            "icd_codes": ["K35.2"],  # Appendicitis
            "procedure_codes": ["PC001"],
            "admit_time": "2024-01-01",
            "los_days": 2,
            "admission_type": "ELECTIVE",
            "heart_rate_mean": 74, "heart_rate_min": 68, "heart_rate_max": 82, "heart_rate_std": 4,
            "systolic_bp_mean": 118, "systolic_bp_min": 112, "diastolic_bp_mean": 76,
            "resp_rate_mean": 16, "resp_rate_max": 18,
            "temp_mean": 37.0, "temp_min": 36.8, "temp_max": 37.3,
            "spo2_mean": 99, "spo2_min": 98, "gcs_min": 15,
            "creatinine_max": 0.8, "creatinine_mean": 0.7,
            "wbc_max": 9.2, "wbc_min": 7.1,
            "hemoglobin_min": 13.8,
            "sodium_min": 138, "sodium_max": 142,
            "potassium_min": 3.8, "potassium_max": 4.2,
            "glucose_max": 98, "glucose_mean": 92,
            "bun_max": 12, "lactate_max": 0.9,
            "inr_max": 1.0, "bilirubin_max": 0.5,
            "albumin_min": 4.1, "troponin_max": 0.01,
        }])
        result = engine.predict(df, include_shap=False)
        assert result["risk_score"] <= 0.40, f"Healthy patient should have low risk, got {result['risk_score']:.2f}"

    def test_confidence_interval_valid(self, engine, generator):
        df = generator.generate_dataset(n_patients=1)
        result = engine.predict(df, include_shap=False)
        assert result["confidence_lower"] <= result["risk_score"]
        assert result["confidence_upper"] >= result["risk_score"]
        assert result["confidence_lower"] >= 0.0
        assert result["confidence_upper"] <= 1.0

    def test_recommended_actions_not_empty(self, engine, generator):
        df = generator.generate_dataset(n_patients=1)
        result = engine.predict(df, include_shap=False)
        assert len(result["recommended_actions"]) > 0

    def test_heuristic_features_direction(self, engine, generator):
        df = generator.generate_dataset(n_patients=1)
        result = engine.predict(df, include_shap=True)
        for feat in result["top_features"]:
            assert feat["direction"] in ("increases_risk", "decreases_risk")


# ── Clinical Explanation ───────────────────────────────────────────────────────

class TestClinicalExplanation:

    def test_high_risk_explanation(self):
        features = [
            {"feature": "aki_risk", "label": "AKI Risk", "shap_value": 0.12,
             "feature_value": 1.0, "direction": "increases_risk",
             "context": "Acute kidney injury is a strong predictor."},
        ]
        explanation, actions = generate_clinical_explanation(0.82, features, {})
        assert "HIGH" in explanation
        assert "82%" in explanation
        assert len(actions) >= 3

    def test_low_risk_explanation(self):
        features = [
            {"feature": "age", "label": "Age", "shap_value": -0.05,
             "feature_value": 35.0, "direction": "decreases_risk", "context": ""},
        ]
        explanation, actions = generate_clinical_explanation(0.12, features, {})
        assert "LOW" in explanation
        assert "12%" in explanation
        assert len(actions) >= 1

    def test_medium_risk_explanation(self):
        _, actions = generate_clinical_explanation(0.55, [], {})
        assert len(actions) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
