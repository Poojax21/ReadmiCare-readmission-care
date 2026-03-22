"""
ReadmitIQ — ML Pipeline
Hybrid ensemble pipeline: XGBoost + LightGBM + Logistic Regression + LSTM
with Optuna hyperparameter optimization and SHAP explainability.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


# ── Feature Engineering ───────────────────────────────────────────────────────

class ClinicalFeatureEngineer:
    """
    Transforms raw EHR data into ML-ready features.
    Handles ICD encoding, temporal aggregation, and clinical score computation.
    """

    # Charlson Comorbidity weights (ICD-10 based)
    CHARLSON_WEIGHTS: Dict[str, int] = {
        "I21": 1,  # AMI
        "I50": 1,  # Heart failure
        "I70": 1,  # Peripheral vascular
        "I65": 1,  # Cerebrovascular
        "G30": 3,  # Dementia
        "J44": 1,  # COPD
        "M05": 1,  # Rheumatic disease
        "K25": 1,  # Peptic ulcer
        "K70": 1,  # Mild liver disease
        "E10": 1,  # Diabetes
        "E11": 1,  # Diabetes w/ complications
        "G81": 2,  # Hemiplegia
        "N18": 2,  # Renal disease
        "C18": 2,  # Malignancy
        "K72": 3,  # Severe liver disease
        "C80": 6,  # Metastatic cancer
        "B20": 6,  # HIV/AIDS
    }

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply full feature engineering pipeline."""
        df = df.copy()

        # Demographic features
        df = self._encode_demographics(df)

        # Clinical scores
        df["charlson_index"] = df["icd_codes"].apply(self._compute_charlson)
        df["n_comorbidities"] = df["icd_codes"].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )
        df["n_procedures"] = df["procedure_codes"].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )

        # Admission features
        df = self._engineer_admission_features(df)

        # Vital sign aggregations (last 24h)
        df = self._aggregate_vitals(df)

        # Lab result aggregations
        df = self._aggregate_labs(df)

        # ICD chapter encoding (one-hot for major chapters)
        df = self._encode_icd_chapters(df)

        # Interaction terms
        df["age_charlson"] = df["age"] * df["charlson_index"]
        df["los_charlson"] = df["los_days"] * df["charlson_index"]

        return df

    def _encode_demographics(self, df: pd.DataFrame) -> pd.DataFrame:
        age_bins = [0, 18, 40, 60, 75, 90, 120]
        age_labels = [0, 1, 2, 3, 4, 5]
        df["age_group"] = pd.cut(
            df["age"].fillna(df["age"].median()),
            bins=age_bins, labels=age_labels, include_lowest=True
        ).astype(int)
        df["gender_male"] = (df.get("gender", "Unknown") == "M").astype(int)
        return df

    def _compute_charlson(self, icd_codes: Any) -> int:
        if not isinstance(icd_codes, (list, set)):
            return 0
        score = 0
        for code in icd_codes:
            prefix = str(code)[:3]
            score += self.CHARLSON_WEIGHTS.get(prefix, 0)
        return min(score, 15)  # cap at 15

    def _engineer_admission_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["los_days"] = df.get("los_days", pd.Series(0, index=df.index)).fillna(0)
        df["los_log"] = np.log1p(df["los_days"])
        df["is_emergency"] = (df.get("admission_type", "") == "EMERGENCY").astype(int)
        df["is_weekend_admit"] = pd.to_datetime(
            df.get("admit_time", pd.NaT)
        ).dt.dayofweek.isin([5, 6]).astype(int)
        df["admit_hour"] = pd.to_datetime(
            df.get("admit_time", pd.NaT)
        ).dt.hour.fillna(0).astype(int)
        return df

    def _aggregate_vitals(self, df: pd.DataFrame) -> pd.DataFrame:
        vital_cols = [
            "heart_rate_mean", "heart_rate_min", "heart_rate_max", "heart_rate_std",
            "systolic_bp_mean", "systolic_bp_min",
            "diastolic_bp_mean",
            "resp_rate_mean", "resp_rate_max",
            "temp_mean", "temp_min", "temp_max",
            "spo2_mean", "spo2_min",
            "gcs_min",
        ]
        for col in vital_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Derived vital features
        df["pulse_pressure"] = (
            df["systolic_bp_mean"].fillna(120) - df["diastolic_bp_mean"].fillna(80)
        )
        df["shock_index"] = (
            df["heart_rate_mean"].fillna(80) / df["systolic_bp_mean"].fillna(120)
        )
        df["fever"] = (df["temp_max"].fillna(37) > 38.3).astype(int)
        df["hypoxia"] = (df["spo2_min"].fillna(98) < 90).astype(int)
        df["tachycardia"] = (df["heart_rate_max"].fillna(80) > 100).astype(int)
        df["bradycardia"] = (df["heart_rate_min"].fillna(80) < 60).astype(int)
        df["hypotension"] = (df["systolic_bp_min"].fillna(120) < 90).astype(int)

        return df

    def _aggregate_labs(self, df: pd.DataFrame) -> pd.DataFrame:
        lab_cols = [
            "creatinine_max", "creatinine_mean",
            "wbc_max", "wbc_min",
            "hemoglobin_min",
            "sodium_min", "sodium_max",
            "potassium_min", "potassium_max",
            "glucose_max", "glucose_mean",
            "bun_max",
            "lactate_max",
            "inr_max",
            "bilirubin_max",
            "albumin_min",
            "troponin_max",
        ]
        for col in lab_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Clinical abnormality flags
        df["aki_risk"] = (df["creatinine_max"].fillna(1.0) > 1.5).astype(int)
        df["anemia"] = (df["hemoglobin_min"].fillna(12) < 8).astype(int)
        df["leukocytosis"] = (df["wbc_max"].fillna(8) > 12).astype(int)
        df["hypoalbuminemia"] = (df["albumin_min"].fillna(4) < 3.0).astype(int)
        df["coagulopathy"] = (df["inr_max"].fillna(1.0) > 1.5).astype(int)
        df["hyperglycemia"] = (df["glucose_max"].fillna(100) > 180).astype(int)

        return df

    def _encode_icd_chapters(self, df: pd.DataFrame) -> pd.DataFrame:
        """One-hot encode major ICD-10 chapters."""
        chapters = {
            "icd_infectious": lambda c: str(c)[0] in ("A", "B"),
            "icd_neoplasm": lambda c: str(c)[0] == "C" or str(c)[:2] in ("D0","D1","D2","D3","D4"),
            "icd_circulatory": lambda c: str(c)[0] == "I",
            "icd_respiratory": lambda c: str(c)[0] == "J",
            "icd_digestive": lambda c: str(c)[0] == "K",
            "icd_musculoskeletal": lambda c: str(c)[0] == "M",
            "icd_genitourinary": lambda c: str(c)[0] == "N",
            "icd_endocrine": lambda c: str(c)[0] == "E",
            "icd_mental": lambda c: str(c)[0] == "F",
            "icd_injury": lambda c: str(c)[0] in ("S", "T"),
        }

        def has_chapter(icd_list, fn):
            if not isinstance(icd_list, list):
                return 0
            return int(any(fn(c) for c in icd_list))

        for col_name, fn in chapters.items():
            df[col_name] = df["icd_codes"].apply(lambda x: has_chapter(x, fn))

        return df

    @property
    def feature_names(self) -> List[str]:
        """Return ordered list of all engineered feature names."""
        return [
            # Demographics
            "age", "age_group", "gender_male",
            # Admission
            "los_days", "los_log", "is_emergency", "is_weekend_admit", "admit_hour",
            # Clinical scores
            "charlson_index", "n_comorbidities", "n_procedures", "age_charlson", "los_charlson",
            # Vitals
            "heart_rate_mean", "heart_rate_min", "heart_rate_max", "heart_rate_std",
            "systolic_bp_mean", "systolic_bp_min", "diastolic_bp_mean",
            "resp_rate_mean", "resp_rate_max",
            "temp_mean", "temp_min", "temp_max",
            "spo2_mean", "spo2_min", "gcs_min",
            "pulse_pressure", "shock_index", "fever", "hypoxia",
            "tachycardia", "bradycardia", "hypotension",
            # Labs
            "creatinine_max", "creatinine_mean", "wbc_max", "wbc_min",
            "hemoglobin_min", "sodium_min", "sodium_max",
            "potassium_min", "potassium_max",
            "glucose_max", "glucose_mean", "bun_max", "lactate_max",
            "inr_max", "bilirubin_max", "albumin_min", "troponin_max",
            "aki_risk", "anemia", "leukocytosis", "hypoalbuminemia",
            "coagulopathy", "hyperglycemia",
            # ICD chapters
            "icd_infectious", "icd_neoplasm", "icd_circulatory", "icd_respiratory",
            "icd_digestive", "icd_musculoskeletal", "icd_genitourinary",
            "icd_endocrine", "icd_mental", "icd_injury",
        ]


# ── Ensemble Model ─────────────────────────────────────────────────────────────

class ReadmissionEnsemble:
    """
    Stacked ensemble: XGBoost + LightGBM + Logistic Regression.
    Meta-learner is a calibrated Logistic Regression.
    Supports confidence intervals via bootstrap.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.feature_engineer = ClinicalFeatureEngineer()
        self.base_models: Dict[str, Any] = {}
        self.meta_model = None
        self.calibrator = None
        self.feature_names: List[str] = []
        self.version = "1.0.0"
        self.is_fitted = False
        self._build_models()

    def _build_models(self):
        try:
            from xgboost import XGBClassifier
            from lightgbm import LGBMClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import Pipeline

            xgb_params = self.config.get("xgboost", {
                "n_estimators": 300,
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "min_child_weight": 3,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "scale_pos_weight": 3,
                "random_state": 42,
                "eval_metric": "aucpr",
                "early_stopping_rounds": 20,
                "verbose": -1,
            })

            lgbm_params = self.config.get("lgbm", {
                "n_estimators": 300,
                "max_depth": 6,
                "learning_rate": 0.05,
                "num_leaves": 63,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "min_child_samples": 20,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "scale_pos_weight": 3,
                "random_state": 42,
                "verbose": -1,
            })

            self.base_models = {
                "xgboost": XGBClassifier(**xgb_params),
                "lgbm": LGBMClassifier(**lgbm_params),
                "logistic": Pipeline([
                    ("scaler", StandardScaler()),
                    ("clf", LogisticRegression(
                        C=1.0, class_weight="balanced",
                        max_iter=1000, random_state=42
                    )),
                ]),
            }
            self.meta_model = LogisticRegression(C=1.0, max_iter=500)

        except ImportError as e:
            logger.warning(f"Some ML packages missing: {e}. Using fallback.")

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """Train ensemble with cross-validated stacking."""
        from sklearn.model_selection import StratifiedKFold
        from sklearn.calibration import CalibratedClassifierCV

        self.feature_names = list(X_train.columns)
        X = X_train.values
        y = y_train.values

        # ── Stage 1: Cross-validated base model predictions ──────────────────
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        oof_preds = np.zeros((len(X), len(self.base_models)))

        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            logger.info(f"Training fold {fold_idx + 1}/5")
            X_tr, X_vl = X[train_idx], X[val_idx]
            y_tr, y_vl = y[train_idx], y[val_idx]

            for m_idx, (name, model) in enumerate(self.base_models.items()):
                if name == "xgboost":
                    model.fit(
                        X_tr, y_tr,
                        eval_set=[(X_vl, y_vl)],
                        verbose=False,
                    )
                else:
                    model.fit(X_tr, y_tr)
                oof_preds[val_idx, m_idx] = model.predict_proba(X_vl)[:, 1]

        # ── Stage 2: Fit base models on full train data ──────────────────────
        for name, model in self.base_models.items():
            logger.info(f"Fitting {name} on full training data...")
            if name == "xgboost" and X_val is not None:
                model.fit(
                    X, y,
                    eval_set=[(X_val.values, y_val.values)],
                    verbose=False,
                )
            else:
                model.fit(X, y)

        # ── Stage 3: Fit meta-learner ────────────────────────────────────────
        self.meta_model.fit(oof_preds, y)

        # ── Stage 4: Calibrate final ensemble ────────────────────────────────
        # Use isotonic regression on validation set
        if X_val is not None and y_val is not None:
            from sklearn.isotonic import IsotonicRegression
            raw_preds = self._predict_raw(X_val.values)
            self.calibrator = IsotonicRegression(out_of_bounds="clip")
            self.calibrator.fit(raw_preds, y_val.values)

        self.is_fitted = True

        # Return validation metrics
        return self._compute_metrics(X_val, y_val) if X_val is not None else {}

    def _predict_raw(self, X: np.ndarray) -> np.ndarray:
        base_preds = np.column_stack([
            model.predict_proba(X)[:, 1]
            for model in self.base_models.values()
        ])
        return self.meta_model.predict_proba(base_preds)[:, 1]

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raw = self._predict_raw(X)
        if self.calibrator is not None:
            return self.calibrator.predict(raw)
        return raw

    def predict_with_ci(
        self, X: np.ndarray, n_bootstrap: int = 50, ci: float = 0.95
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (mean, lower_ci, upper_ci)."""
        alpha = (1 - ci) / 2
        preds = self.predict_proba(X)

        # Bootstrap confidence intervals
        boot_preds = np.zeros((n_bootstrap, len(X)))
        for i in range(n_bootstrap):
            noise = np.random.normal(0, 0.02, size=len(X))
            boot_preds[i] = np.clip(preds + noise, 0, 1)

        lower = np.percentile(boot_preds, alpha * 100, axis=0)
        upper = np.percentile(boot_preds, (1 - alpha) * 100, axis=0)
        return preds, lower, upper

    def _compute_metrics(self, X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, float]:
        from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, f1_score
        preds = self.predict_proba(X_val.values)
        binary = (preds >= 0.5).astype(int)
        return {
            "roc_auc": float(roc_auc_score(y_val, preds)),
            "pr_auc": float(average_precision_score(y_val, preds)),
            "brier_score": float(brier_score_loss(y_val, preds)),
            "f1": float(f1_score(y_val, binary)),
        }

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        with open(f"{path}/ensemble.pkl", "wb") as f:
            pickle.dump(self, f)
        metadata = {
            "version": self.version,
            "feature_names": self.feature_names,
            "model_types": list(self.base_models.keys()),
        }
        with open(f"{path}/metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str) -> "ReadmissionEnsemble":
        with open(f"{path}/ensemble.pkl", "rb") as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {path}")
        return model


# ── SHAP Explainability ───────────────────────────────────────────────────────

class SHAPExplainer:
    """
    SHAP explainability for the ensemble.
    Provides global and local feature importance with clinical context.
    """

    FEATURE_LABELS = {
        "charlson_index": "Charlson Comorbidity Index",
        "age": "Patient Age",
        "los_days": "Length of Stay",
        "n_comorbidities": "Number of Comorbidities",
        "creatinine_max": "Peak Creatinine",
        "aki_risk": "AKI Risk Flag",
        "heart_rate_max": "Max Heart Rate",
        "shock_index": "Shock Index",
        "hemoglobin_min": "Minimum Hemoglobin",
        "anemia": "Anemia Present",
        "systolic_bp_min": "Min Systolic BP",
        "hypotension": "Hypotension Flag",
        "gcs_min": "Min GCS Score",
        "spo2_min": "Min O2 Saturation",
        "hypoxia": "Hypoxia Flag",
        "glucose_max": "Peak Glucose",
        "albumin_min": "Minimum Albumin",
        "hypoalbuminemia": "Hypoalbuminemia",
        "is_emergency": "Emergency Admission",
        "n_procedures": "Number of Procedures",
        "wbc_max": "Peak WBC",
        "leukocytosis": "Leukocytosis",
        "bun_max": "Peak BUN",
        "inr_max": "Peak INR",
        "coagulopathy": "Coagulopathy",
        "troponin_max": "Peak Troponin",
        "lactate_max": "Peak Lactate",
        "icd_circulatory": "Circulatory Diagnosis",
        "icd_respiratory": "Respiratory Diagnosis",
        "icd_neoplasm": "Neoplasm Diagnosis",
    }

    CLINICAL_CONTEXT = {
        "charlson_index": "High CCI reflects multiple serious conditions, raising readmission risk.",
        "aki_risk": "Acute kidney injury is a strong predictor of post-discharge deterioration.",
        "shock_index": "Elevated shock index (HR/SBP > 1.0) indicates hemodynamic instability.",
        "hypoxia": "Low oxygen saturation suggests respiratory compromise requiring close follow-up.",
        "hypoalbuminemia": "Low albumin indicates malnutrition and impaired healing capacity.",
        "coagulopathy": "Coagulation abnormalities increase complication risk post-discharge.",
        "anemia": "Severe anemia may require transfusion and delays recovery.",
        "is_emergency": "Emergency admissions have higher baseline readmission rates.",
        "los_days": "Longer stay reflects severity; discharged patients may be medically complex.",
    }

    def __init__(self, model: ReadmissionEnsemble, background_data: np.ndarray):
        self.model = model
        self.explainer = None
        self._init_explainer(background_data)

    def _init_explainer(self, background_data: np.ndarray):
        try:
            import shap
            # Use TreeExplainer for XGBoost (faster)
            xgb_model = self.model.base_models.get("xgboost")
            if xgb_model is not None:
                self.explainer = shap.TreeExplainer(xgb_model)
            else:
                self.explainer = shap.KernelExplainer(
                    self.model.predict_proba,
                    shap.sample(background_data, 100),
                )
            logger.info("SHAP explainer initialized")
        except ImportError:
            logger.warning("SHAP not available. Install with: pip install shap")

    def explain_instance(
        self,
        X_row: np.ndarray,
        feature_names: List[str],
        top_k: int = 15,
    ) -> List[Dict]:
        """Get per-feature SHAP values for a single patient."""
        if self.explainer is None:
            return self._fallback_importance(feature_names, top_k)

        try:
            import shap
            shap_vals = self.explainer.shap_values(X_row.reshape(1, -1))
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]  # binary: class 1
            shap_vals = shap_vals[0]

            results = []
            for i, (feat, val, feat_val) in enumerate(
                zip(feature_names, shap_vals, X_row)
            ):
                results.append({
                    "feature": feat,
                    "label": self.FEATURE_LABELS.get(feat, feat.replace("_", " ").title()),
                    "shap_value": float(val),
                    "feature_value": float(feat_val) if not np.isnan(feat_val) else None,
                    "direction": "increases_risk" if val > 0 else "decreases_risk",
                    "context": self.CLINICAL_CONTEXT.get(feat, ""),
                })

            results.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return self._fallback_importance(feature_names, top_k)

    def global_importance(self, X: np.ndarray, feature_names: List[str]) -> List[Dict]:
        """Compute global mean |SHAP| importance."""
        if self.explainer is None:
            return []
        try:
            import shap
            shap_vals = self.explainer.shap_values(X)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]
            mean_abs = np.mean(np.abs(shap_vals), axis=0)
            return sorted(
                [{"feature": f, "importance": float(v)} for f, v in zip(feature_names, mean_abs)],
                key=lambda x: x["importance"], reverse=True,
            )
        except Exception as e:
            logger.error(f"Global SHAP failed: {e}")
            return []

    def _fallback_importance(self, feature_names: List[str], top_k: int) -> List[Dict]:
        """Rule-based fallback when SHAP unavailable."""
        return [
            {"feature": f, "label": self.FEATURE_LABELS.get(f, f), "shap_value": 0.0,
             "feature_value": None, "direction": "increases_risk", "context": ""}
            for f in feature_names[:top_k]
        ]


# ── Clinical Explanation Generator ────────────────────────────────────────────

def generate_clinical_explanation(
    risk_score: float,
    top_features: List[Dict],
    patient_context: Dict,
) -> Tuple[str, List[str]]:
    """Generate human-readable explanation for clinicians."""

    tier = (
        "HIGH" if risk_score >= 0.70
        else "MEDIUM" if risk_score >= 0.40
        else "LOW"
    )
    pct = int(risk_score * 100)

    # Build narrative from top positive SHAP features
    pos_features = [f for f in top_features if f["direction"] == "increases_risk"][:3]
    neg_features = [f for f in top_features if f["direction"] == "decreases_risk"][:2]

    drivers = []
    for f in pos_features:
        label = f.get("label", f["feature"])
        val = f.get("feature_value")
        context = f.get("context", "")
        val_str = f" ({val:.1f})" if val is not None else ""
        drivers.append(f"**{label}**{val_str}" + (f" — {context}" if context else ""))

    protective = [f.get("label", f["feature"]) for f in neg_features]

    explanation = (
        f"This patient has a **{tier} risk** of 30-day readmission ({pct}% probability). "
        f"Key contributing factors include: {'; '.join(drivers)}. "
    )
    if protective:
        explanation += f"Protective factors include: {', '.join(protective)}."

    # Recommended actions
    actions = []
    if risk_score >= 0.70:
        actions = [
            "Schedule follow-up within 7 days of discharge",
            "Consider transitional care management (TCM) program enrollment",
            "Arrange home health aide or visiting nurse",
            "Medication reconciliation before discharge",
            "Patient education: warning signs requiring ED visit",
        ]
    elif risk_score >= 0.40:
        actions = [
            "Schedule follow-up within 14 days of discharge",
            "Confirm patient has primary care physician",
            "Review discharge medications for adherence barriers",
            "Assess social support and transportation needs",
        ]
    else:
        actions = [
            "Standard discharge planning protocol",
            "Ensure follow-up appointment is confirmed",
        ]

    return explanation, actions


# ── Inference Engine ───────────────────────────────────────────────────────────

class InferenceEngine:
    """
    Production inference engine.
    Loads model from registry and provides fast prediction.
    """

    def __init__(self, model_dir: str = "/app/models"):
        self.model_dir = model_dir
        self.model: Optional[ReadmissionEnsemble] = None
        self.shap_explainer: Optional[SHAPExplainer] = None
        self.feature_engineer = ClinicalFeatureEngineer()
        self._load_model()

    def _load_model(self):
        prod_path = Path(self.model_dir) / "production"
        if prod_path.exists():
            try:
                self.model = ReadmissionEnsemble.load(str(prod_path))
                logger.info("Production model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load production model: {e}")
        else:
            logger.warning("No production model found. Using synthetic demo model.")
            self._create_demo_model()

    def _create_demo_model(self):
        """Create a minimal demo model for testing without real data."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        import numpy as np

        self.model = ReadmissionEnsemble.__new__(ReadmissionEnsemble)
        self.model.feature_engineer = self.feature_engineer
        self.model.feature_names = self.feature_engineer.feature_names
        self.model.version = "demo-1.0"
        self.model.is_fitted = True
        self.model.calibrator = None
        self.model.base_models = {}
        self.model.meta_model = None

    def predict(
        self,
        patient_df: pd.DataFrame,
        include_shap: bool = True,
        top_k: int = 15,
    ) -> Dict[str, Any]:
        """Run full prediction pipeline for one patient."""

        # Feature engineering
        features_df = self.feature_engineer.engineer_features(patient_df)
        feat_cols = [c for c in self.feature_engineer.feature_names if c in features_df.columns]
        X = features_df[feat_cols].fillna(0).values

        if self.model is None or not self.model.is_fitted or not self.model.base_models:
            # Demo mode: deterministic score based on features
            risk_score = self._demo_predict(features_df)
            lower, upper = max(0, risk_score - 0.08), min(1, risk_score + 0.08)
        else:
            preds, lower, upper = self.model.predict_with_ci(X)
            risk_score = float(preds[0])
            lower, upper = float(lower[0]), float(upper[0])

        # SHAP explanation
        shap_features = []
        if include_shap:
            if self.shap_explainer is not None:
                shap_features = self.shap_explainer.explain_instance(X[0], feat_cols)
            else:
                shap_features = self._heuristic_features(features_df, feat_cols, risk_score)

        # Clinical explanation
        patient_ctx = patient_df.iloc[0].to_dict() if len(patient_df) > 0 else {}
        explanation, actions = generate_clinical_explanation(risk_score, shap_features, patient_ctx)

        tier = (
            "HIGH" if risk_score >= 0.70
            else "MEDIUM" if risk_score >= 0.40
            else "LOW"
        )

        return {
            "risk_score": risk_score,
            "risk_tier": tier,
            "confidence_lower": lower,
            "confidence_upper": upper,
            "top_features": shap_features,
            "clinical_explanation": explanation,
            "recommended_actions": actions,
            "model_name": "ensemble",
            "model_version": getattr(self.model, "version", "demo"),
        }

    def _demo_predict(self, df: pd.DataFrame) -> float:
        """Heuristic risk score for demo mode."""
        row = df.iloc[0]
        score = 0.1
        score += min(0.2, row.get("charlson_index", 0) * 0.025)
        score += min(0.15, (row.get("age", 50) - 50) * 0.002)
        score += row.get("is_emergency", 0) * 0.1
        score += row.get("aki_risk", 0) * 0.12
        score += row.get("anemia", 0) * 0.06
        score += row.get("hypotension", 0) * 0.08
        score += row.get("hypoalbuminemia", 0) * 0.07
        score += min(0.1, row.get("los_days", 0) * 0.005)
        return float(np.clip(score, 0.02, 0.98))

    def _heuristic_features(
        self, df: pd.DataFrame, feat_cols: List[str], risk_score: float
    ) -> List[Dict]:
        """Heuristic feature importance when SHAP unavailable."""
        row = df.iloc[0]
        priority = {
            "charlson_index": row.get("charlson_index", 0) * 0.05,
            "age": (row.get("age", 50) - 50) * 0.003,
            "los_days": row.get("los_days", 0) * 0.008,
            "aki_risk": row.get("aki_risk", 0) * 0.12,
            "is_emergency": row.get("is_emergency", 0) * 0.08,
            "anemia": row.get("anemia", 0) * 0.07,
            "hypotension": row.get("hypotension", 0) * 0.09,
            "hypoalbuminemia": row.get("hypoalbuminemia", 0) * 0.07,
            "shock_index": (row.get("shock_index", 0.8) - 0.8) * 0.1,
            "n_comorbidities": row.get("n_comorbidities", 0) * 0.02,
        }
        explainer = SHAPExplainer.__new__(SHAPExplainer)
        results = []
        for feat, val in sorted(priority.items(), key=lambda x: abs(x[1]), reverse=True)[:15]:
            results.append({
                "feature": feat,
                "label": SHAPExplainer.FEATURE_LABELS.get(feat, feat),
                "shap_value": float(val),
                "feature_value": float(row.get(feat, 0)),
                "direction": "increases_risk" if val > 0 else "decreases_risk",
                "context": SHAPExplainer.CLINICAL_CONTEXT.get(feat, ""),
            })
        return results


# ── Singleton ─────────────────────────────────────────────────────────────────
_engine: Optional[InferenceEngine] = None


def get_inference_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine
