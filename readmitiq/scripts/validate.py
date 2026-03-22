#!/usr/bin/env python3
"""
ReadmitIQ — Quick System Validation Script
Runs without Docker to verify core ML pipeline works.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

import pandas as pd
import numpy as np
from datetime import datetime

print("=" * 60)
print("🏥 ReadmitIQ — System Validation")
print("=" * 60)


def check(label, fn):
    try:
        result = fn()
        print(f"  ✅ {label}")
        return result
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return None


# ── 1. Synthetic Data Generator ────────────────────────────
print("\n📊 Synthetic Data Generator")
from app.ml.synthetic_data import SyntheticDataGenerator

gen = SyntheticDataGenerator(random_seed=42)

patient = check("Generate patient", gen.generate_patient)
admission = check("Generate admission", lambda: gen.generate_admission(patient))
dataset = check("Generate dataset (n=100)", lambda: gen.generate_dataset(100))
payload = check("Generate API payload", gen.generate_api_payload)

if dataset is not None:
    readmission_rate = dataset["was_readmitted_30d"].mean()
    print(f"     Readmission rate: {readmission_rate:.1%} (target: 10–25%)")
    print(f"     Dataset shape: {dataset.shape}")


# ── 2. Feature Engineering ─────────────────────────────────
print("\n🔧 Feature Engineering")
from app.ml.pipeline import ClinicalFeatureEngineer

eng = ClinicalFeatureEngineer()

features = check("Engineer features on 100 patients", lambda: eng.engineer_features(dataset))
feat_names = check("Feature names", lambda: eng.feature_names)

if features is not None and feat_names is not None:
    available = [c for c in feat_names if c in features.columns]
    print(f"     Total features defined: {len(feat_names)}")
    print(f"     Features available in dataset: {len(available)}")
    print(f"     Missing (will be filled with 0): {len(feat_names) - len(available)}")


# ── 3. Inference Engine ────────────────────────────────────
print("\n🧠 Inference Engine")
from app.ml.pipeline import InferenceEngine

engine = check("Initialize InferenceEngine", lambda: InferenceEngine(model_dir="/tmp/test_models"))

if engine and dataset is not None:
    result = check("Predict single patient (demo mode)",
                   lambda: engine.predict(dataset.head(1), include_shap=True))

    if result:
        score = result["risk_score"]
        tier = result["risk_tier"]
        print(f"     Risk Score: {score:.3f} → {tier}")
        print(f"     CI: [{result['confidence_lower']:.3f}, {result['confidence_upper']:.3f}]")
        print(f"     Top feature: {result['top_features'][0]['feature'] if result['top_features'] else 'N/A'}")
        print(f"     Actions: {len(result['recommended_actions'])} recommendations")


# ── 4. Batch prediction ────────────────────────────────────
print("\n⚡ Batch Inference Performance")
import time

if engine and dataset is not None:
    start = time.time()
    n_batch = 50
    for i in range(n_batch):
        row = dataset.iloc[i % len(dataset): i % len(dataset) + 1]
        engine.predict(row, include_shap=False)
    elapsed = time.time() - start
    print(f"  ✅ {n_batch} predictions in {elapsed:.2f}s ({n_batch/elapsed:.0f}/sec)")


# ── 5. Clinical explanation ────────────────────────────────
print("\n📋 Clinical Explanation")
from app.ml.pipeline import generate_clinical_explanation

features_mock = [
    {"feature": "aki_risk", "label": "AKI Risk", "shap_value": 0.14,
     "feature_value": 1.0, "direction": "increases_risk",
     "context": "Acute kidney injury is a strong predictor."},
    {"feature": "charlson_index", "label": "Charlson Index", "shap_value": 0.10,
     "feature_value": 6.0, "direction": "increases_risk", "context": ""},
    {"feature": "albumin_min", "label": "Albumin (min)", "shap_value": -0.06,
     "feature_value": 2.3, "direction": "decreases_risk", "context": ""},
]

check("Generate HIGH risk explanation",
      lambda: generate_clinical_explanation(0.78, features_mock, {}))
check("Generate LOW risk explanation",
      lambda: generate_clinical_explanation(0.15, features_mock, {}))


# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("✅ Core system validation complete!")
print("\nNext steps:")
print("  1. docker compose up --build    # Launch full stack")
print("  2. http://localhost             # Open dashboard")
print("  3. http://localhost:8000/api/docs  # API docs")
print("=" * 60)
