"""
ReadmitIQ — Synthetic Data Generator
Generates realistic, MIMIC-compatible synthetic patient data without PHI.
Uses statistical distributions derived from MIMIC-III population statistics.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ── Population Statistics (from MIMIC-III) ────────────────────────────────────

ADMISSION_TYPES = ["EMERGENCY", "ELECTIVE", "URGENT", "NEWBORN"]
ADMISSION_WEIGHTS = [0.60, 0.25, 0.13, 0.02]

DISCHARGE_LOCATIONS = [
    "HOME", "HOME HEALTH CARE", "SNF", "REHAB", "LONG TERM CARE",
    "HOSPICE", "DIED", "AMA"
]
DISCHARGE_WEIGHTS = [0.45, 0.18, 0.15, 0.08, 0.06, 0.03, 0.03, 0.02]

ETHNICITIES = [
    "WHITE", "BLACK", "HISPANIC", "ASIAN", "OTHER", "UNKNOWN"
]
ETHNICITY_WEIGHTS = [0.62, 0.15, 0.10, 0.07, 0.04, 0.02]

INSURANCE_TYPES = ["Medicare", "Medicaid", "Private", "Self Pay", "Government"]
INSURANCE_WEIGHTS = [0.48, 0.22, 0.22, 0.05, 0.03]

# ── Realistic Name Pools ──────────────────────────────────────────────────────

FIRST_NAMES_MALE = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
    "Anthony", "Mark", "Donald", "Steven", "Andrew", "Paul", "Joshua",
    "Kenneth", "Kevin", "Brian", "George", "Timothy",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth",
    "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty",
    "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily",
    "Donna", "Michelle", "Carol", "Amanda", "Melissa", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson",
]

ATTENDING_PHYSICIANS = [
    "Dr. Sarah Chen", "Dr. Michael Patel", "Dr. James Wilson",
    "Dr. Emily Rodriguez", "Dr. David Kim", "Dr. Jennifer Park",
    "Dr. Robert Singh", "Dr. Lisa Chang", "Dr. William Torres",
    "Dr. Amanda Foster", "Dr. Christopher Lee", "Dr. Rachel Green",
    "Dr. Daniel Brooks", "Dr. Maria Santos", "Dr. Andrew Webb",
]

WARDS = [
    "Cardiology 4A", "Medical ICU", "Cardiac ICU", "General Medicine 3B",
    "Pulmonary 5C", "Surgical ICU", "Neurology 2A", "Oncology 6B",
    "General Medicine 4C", "Telemetry 3A", "Step-Down Unit",
]

ICD10_DIAGNOSES = {
    # Circulatory
    "I50.9": ("Heart failure, unspecified", 0.08),
    "I21.9": ("Acute MI, unspecified", 0.06),
    "I10":   ("Essential hypertension", 0.07),
    "I48.0": ("Atrial fibrillation, paroxysmal", 0.05),
    "I63.9": ("Cerebral infarction, unspecified", 0.03),
    # Respiratory
    "J44.1": ("COPD with exacerbation", 0.07),
    "J18.9": ("Pneumonia, unspecified", 0.06),
    "J96.0": ("Acute respiratory failure", 0.04),
    # Endocrine / Metabolic
    "E11.65": ("Type 2 DM with hyperglycemia", 0.06),
    "E86.0": ("Dehydration", 0.03),
    # Digestive
    "K92.1": ("GI bleed", 0.04),
    "K74.6": ("Liver cirrhosis, other", 0.03),
    # Renal
    "N17.9": ("AKI, unspecified", 0.05),
    "N18.6": ("CKD stage 5", 0.04),
    # Neoplasm
    "C78.89": ("Secondary malignant neoplasm", 0.03),
    "C80.1": ("Malignant neoplasm, unspecified", 0.03),
    # Sepsis
    "A41.9": ("Sepsis, unspecified", 0.06),
    "A40.9": ("Streptococcal sepsis, unspecified", 0.02),
}

LAB_DISTRIBUTIONS = {
    # (mean, std, min_normal, max_normal)
    "Creatinine":   (1.2,  0.9,  0.6,  1.2),
    "WBC":          (9.5,  5.0,  4.0,  11.0),
    "Hemoglobin":   (11.2, 2.5,  12.0, 17.0),
    "Sodium":       (138,  5.0,  136,  145),
    "Potassium":    (4.1,  0.8,  3.5,  5.0),
    "Glucose":      (140,  60,   70,   100),
    "BUN":          (22,   15,   7,    20),
    "Lactate":      (2.1,  1.8,  0.5,  2.0),
    "INR":          (1.3,  0.5,  0.9,  1.2),
    "Bilirubin":    (1.2,  1.5,  0.2,  1.2),
    "Albumin":      (3.2,  0.7,  3.5,  5.0),
    "Troponin":     (0.5,  2.0,  0.0,  0.04),
}


class SyntheticDataGenerator:
    """
    Generates statistically realistic synthetic hospital admission data.
    Outcome (30-day readmission) is calibrated to real ~15% prevalence
    with higher rates for high-risk feature combinations.
    """

    def __init__(self, random_seed: int = 42):
        np.random.seed(random_seed)
        random.seed(random_seed)
        self.rng = np.random.default_rng(random_seed)

    def generate_patient(self) -> Dict[str, Any]:
        """Generate a single synthetic patient with full demographics."""
        age = int(np.clip(self.rng.normal(65, 18), 18, 100))
        gender = random.choice(["M", "F"])
        ethnicity = random.choices(ETHNICITIES, weights=ETHNICITY_WEIGHTS)[0]
        insurance = random.choices(INSURANCE_TYPES, weights=INSURANCE_WEIGHTS)[0]

        # Generate realistic name
        if gender == "M":
            first_name = random.choice(FIRST_NAMES_MALE)
        else:
            first_name = random.choice(FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)

        # Generate date of birth from age
        dob = datetime.now(timezone.utc) - timedelta(days=age * 365 + random.randint(0, 364))

        # Generate phone number
        area_code = random.randint(200, 999)
        phone_mid = random.randint(200, 999)
        phone_end = random.randint(1000, 9999)
        phone = f"({area_code}) {phone_mid}-{phone_end}"

        # Attending physician and ward
        attending = random.choice(ATTENDING_PHYSICIANS)
        ward = random.choice(WARDS)

        # Primary diagnosis
        icd_codes_pool = list(ICD10_DIAGNOSES.keys())
        icd_weights_pool = [v[1] for v in ICD10_DIAGNOSES.values()]
        primary_icd = random.choices(icd_codes_pool, weights=icd_weights_pool)[0]
        primary_diagnosis_name = ICD10_DIAGNOSES[primary_icd][0]

        # Additional comorbidities (0–5)
        n_comorbidities = int(self.rng.integers(0, 6))
        comorbidities = random.sample(
            [c for c in icd_codes_pool if c != primary_icd],
            min(int(n_comorbidities), len(icd_codes_pool) - 1),
        )

        return {
            "id": str(uuid.uuid4()),
            "mrn": f"MRN{random.randint(100000, 999999)}",
            "first_name": first_name,
            "last_name": last_name,
            "full_name": f"{first_name} {last_name}",
            "date_of_birth": dob.strftime("%Y-%m-%d"),
            "phone": phone,
            "age": age,
            "gender": gender,
            "ethnicity": ethnicity,
            "insurance_type": insurance,
            "attending_physician": attending,
            "ward": ward,
            "primary_diagnosis_icd": primary_icd,
            "primary_diagnosis_name": primary_diagnosis_name,
            "comorbidities": comorbidities,
        }

    def generate_admission(self, patient: Dict) -> Dict[str, Any]:
        """Generate admission details for a patient."""
        admit_time = datetime.now(timezone.utc) - timedelta(
            days=int(self.rng.integers(0, 365))
        )

        los_days = float(np.clip(
            self.rng.exponential(scale=5.0) + 1.0, 1.0, 60.0
        ))
        discharge_time = admit_time + timedelta(days=los_days)

        admission_type = random.choices(ADMISSION_TYPES, weights=ADMISSION_WEIGHTS)[0]
        drg = f"{random.randint(100, 999)}"

        # All ICD codes
        all_icd = [patient["primary_diagnosis_icd"]] + patient.get("comorbidities", [])

        # Generate vitals (24h summary)
        vitals = self._generate_vitals_summary(patient["age"], admission_type)

        # Generate labs
        labs = self._generate_labs_summary(all_icd)

        # Compute readmission probability
        risk = self._compute_risk(patient, los_days, admission_type, vitals, labs)
        was_readmitted = bool(self.rng.random() < risk)

        return {
            "id": str(uuid.uuid4()),
            "patient_id": patient["id"],
            "hadm_id": f"HADM{random.randint(1000000, 9999999)}",
            "admit_time": admit_time.isoformat(),
            "discharge_time": discharge_time.isoformat(),
            "los_days": round(los_days, 1),
            "admission_type": admission_type,
            "drg_code": drg,
            "icd_codes": all_icd,
            "procedure_codes": [f"PC{random.randint(100, 999)}" for _ in range(self.rng.integers(0, 5))],
            "was_readmitted_30d": was_readmitted,
            **vitals,
            **labs,
        }

    def _generate_vitals_summary(self, age: int, admission_type: str) -> Dict:
        severity = 1.5 if admission_type == "EMERGENCY" else 1.0

        hr_base = 80 + (age - 50) * 0.2 + self.rng.normal(0, 10 * severity)
        sbp_base = 125 - (age - 50) * 0.1 + self.rng.normal(0, 15 * severity)

        return {
            "heart_rate_mean": float(np.clip(hr_base, 45, 180)),
            "heart_rate_min":  float(np.clip(hr_base - abs(self.rng.normal(10, 5)), 40, 160)),
            "heart_rate_max":  float(np.clip(hr_base + abs(self.rng.normal(15, 8)), 50, 200)),
            "heart_rate_std":  float(abs(self.rng.normal(8, 3))),
            "systolic_bp_mean": float(np.clip(sbp_base, 70, 200)),
            "systolic_bp_min":  float(np.clip(sbp_base - abs(self.rng.normal(20, 8)), 60, 180)),
            "diastolic_bp_mean": float(np.clip(sbp_base * 0.65, 40, 120)),
            "resp_rate_mean": float(np.clip(self.rng.normal(18 * severity, 4), 8, 40)),
            "resp_rate_max":  float(np.clip(self.rng.normal(24 * severity, 5), 10, 50)),
            "temp_mean": float(np.clip(self.rng.normal(37.2 + (0.5 if admission_type == "EMERGENCY" else 0), 0.6), 35, 41)),
            "temp_min":  float(np.clip(self.rng.normal(36.8, 0.4), 34.5, 39)),
            "temp_max":  float(np.clip(self.rng.normal(38.0 + (0.5 if admission_type == "EMERGENCY" else 0), 0.8), 36, 42)),
            "spo2_mean": float(np.clip(self.rng.normal(96, 3), 70, 100)),
            "spo2_min":  float(np.clip(self.rng.normal(93, 5), 60, 100)),
            "gcs_min":   int(np.clip(self.rng.normal(13, 2.5), 3, 15)),
        }

    def _generate_labs_summary(self, icd_codes: List[str]) -> Dict:
        # Adjust distributions based on diagnoses
        has_renal = any(c.startswith(("N17", "N18")) for c in icd_codes)
        has_sepsis = any(c.startswith("A4") for c in icd_codes)
        has_gi = any(c.startswith(("K7", "K9")) for c in icd_codes)

        creatinine_mean = 1.8 if has_renal else 1.2
        wbc_mean = 16 if has_sepsis else 9.5
        bilirubin_mean = 3.5 if has_gi else 1.2
        lactate_mean = 3.5 if has_sepsis else 1.8

        def sample(mean, std, low=0, high=50):
            return float(np.clip(self.rng.normal(mean, std), low, high))

        return {
            "creatinine_max":  sample(creatinine_mean + 0.5, 1.2, 0.3, 20),
            "creatinine_mean": sample(creatinine_mean, 0.8, 0.3, 15),
            "wbc_max":  sample(wbc_mean + 3, 6, 1, 60),
            "wbc_min":  sample(wbc_mean - 2, 3, 0.5, 30),
            "hemoglobin_min": sample(10.5, 2.5, 4, 18),
            "sodium_min": sample(136, 6, 115, 155),
            "sodium_max": sample(140, 4, 120, 160),
            "potassium_min": sample(3.8, 0.7, 2, 7),
            "potassium_max": sample(4.5, 0.8, 2.5, 8),
            "glucose_max":  sample(180, 80, 50, 600),
            "glucose_mean": sample(140, 50, 50, 400),
            "bun_max": sample(28, 18, 5, 150),
            "lactate_max": sample(lactate_mean + 0.5, 1.5, 0.3, 15),
            "inr_max": sample(1.4, 0.6, 0.8, 8),
            "bilirubin_max": sample(bilirubin_mean + 0.5, 2, 0.1, 30),
            "albumin_min": sample(3.0, 0.7, 1, 5.5),
            "troponin_max": sample(0.5, 2.0, 0, 50),
        }

    def _compute_risk(
        self,
        patient: Dict,
        los_days: float,
        admission_type: str,
        vitals: Dict,
        labs: Dict,
    ) -> float:
        """Compute realistic readmission probability."""
        score = 0.08  # base rate

        # Age risk
        score += max(0, (patient["age"] - 60) * 0.003)

        # Comorbidity burden
        score += len(patient.get("comorbidities", [])) * 0.02

        # Admission type
        if admission_type == "EMERGENCY":
            score += 0.06

        # LOS
        score += min(0.10, los_days * 0.005)

        # Lab abnormalities
        if labs["creatinine_max"] > 2.0: score += 0.08
        if labs["hemoglobin_min"] < 8.0: score += 0.06
        if labs["albumin_min"] < 2.5: score += 0.07
        if labs["lactate_max"] > 4.0: score += 0.06
        if labs["inr_max"] > 2.0: score += 0.05

        # Vital abnormalities
        if vitals["systolic_bp_min"] < 85: score += 0.07
        if vitals["spo2_min"] < 88: score += 0.06
        if vitals["gcs_min"] < 10: score += 0.05

        return float(np.clip(score + self.rng.normal(0, 0.03), 0.01, 0.95))

    def generate_dataset(
        self,
        n_patients: int = 500,
        as_dataframe: bool = True,
    ) -> pd.DataFrame | List[Dict]:
        """Generate a complete synthetic dataset."""
        records = []
        for _ in range(n_patients):
            patient = self.generate_patient()
            admission = self.generate_admission(patient)
            record = {**patient, **admission}
            # Add derived fields
            record["icd_codes"] = record.get("icd_codes", [])
            record["procedure_codes"] = record.get("procedure_codes", [])
            records.append(record)

        if as_dataframe:
            return pd.DataFrame(records)
        return records

    def generate_api_payload(self) -> Dict:
        """Generate a single patient payload matching the API schema."""
        patient = self.generate_patient()
        admission = self.generate_admission(patient)
        vitals_series = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=24)
        for h in range(0, 24, 4):
            vitals_series.append({
                "chart_time": (base_time + timedelta(hours=h)).isoformat(),
                "heart_rate": float(np.clip(self.rng.normal(admission["heart_rate_mean"], 8), 40, 200)),
                "systolic_bp": float(np.clip(self.rng.normal(admission["systolic_bp_mean"], 12), 60, 200)),
                "diastolic_bp": float(np.clip(self.rng.normal(admission["diastolic_bp_mean"], 8), 30, 130)),
                "respiratory_rate": float(np.clip(self.rng.normal(admission["resp_rate_mean"], 3), 8, 50)),
                "temperature": float(np.clip(self.rng.normal(admission["temp_mean"], 0.4), 35, 41)),
                "spo2": float(np.clip(self.rng.normal(admission["spo2_mean"], 2), 70, 100)),
                "gcs_total": int(admission["gcs_min"]),
            })

        return {
            "patient_data": {
                "patient_id": patient["id"],
                "admit_time": admission["admit_time"],
                "admission_type": admission["admission_type"],
                "icd_codes": admission["icd_codes"],
                "procedure_codes": admission["procedure_codes"],
                "vitals": vitals_series,
                "labs": [
                    {"chart_time": base_time.isoformat(), "label": "Creatinine", "value": admission["creatinine_max"], "unit": "mg/dL"},
                    {"chart_time": base_time.isoformat(), "label": "WBC", "value": admission["wbc_max"], "unit": "K/uL"},
                    {"chart_time": base_time.isoformat(), "label": "Hemoglobin", "value": admission["hemoglobin_min"], "unit": "g/dL"},
                    {"chart_time": base_time.isoformat(), "label": "Albumin", "value": admission["albumin_min"], "unit": "g/dL"},
                    {"chart_time": base_time.isoformat(), "label": "Lactate", "value": admission["lactate_max"], "unit": "mmol/L"},
                ],
            },
            "patient_info": patient,
            "true_readmission": admission["was_readmitted_30d"],
        }
