#!/usr/bin/env python3
"""
LifeProof AI - Synthetic Medical Data Generator

Generates realistic synthetic Attending Physician Statements (APS) for testing
the medical document summarization pipeline.

Features:
- Multiple risk profiles (High, Medium, Low)
- Realistic clinical narratives and lab values
- Configurable batch sizes
- S3 upload capability
- Local file generation for testing

Usage:
    # Generate 100 files locally
    python gen_synthetic_data.py --count 100 --output ./test_data
    
    # Generate and upload to S3
    python gen_synthetic_data.py --count 2000 --bucket your-bucket-name
    
    # Generate specific risk profiles
    python gen_synthetic_data.py --count 100 --profile high_risk --output ./test_data
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import boto3
    from faker import Faker
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# ============================================================
# CLINICAL DATA TEMPLATES
# ============================================================

CONDITIONS = {
    "high_risk": [
        {"name": "Acute Myocardial Infarction (STEMI)", "icd10": "I21.0"},
        {"name": "Ischemic Stroke", "icd10": "I63.9"},
        {"name": "Non-Small Cell Lung Carcinoma", "icd10": "C34.90"},
        {"name": "End-Stage Renal Disease", "icd10": "N18.6"},
        {"name": "Dilated Cardiomyopathy", "icd10": "I42.0"},
        {"name": "Severe COPD", "icd10": "J44.1"},
        {"name": "Hepatocellular Carcinoma", "icd10": "C22.0"},
    ],
    "medium_risk": [
        {"name": "Type 2 Diabetes Mellitus", "icd10": "E11.9"},
        {"name": "Essential Hypertension", "icd10": "I10"},
        {"name": "Atrial Fibrillation", "icd10": "I48.91"},
        {"name": "Chronic Kidney Disease Stage 3", "icd10": "N18.3"},
        {"name": "Obesity", "icd10": "E66.9"},
        {"name": "Obstructive Sleep Apnea", "icd10": "G47.33"},
        {"name": "Hyperlipidemia", "icd10": "E78.5"},
    ],
    "low_risk": [
        {"name": "Seasonal Allergies", "icd10": "J30.2"},
        {"name": "Vitamin D Deficiency", "icd10": "E55.9"},
        {"name": "Gastroesophageal Reflux", "icd10": "K21.0"},
        {"name": "Benign Prostatic Hyperplasia", "icd10": "N40.0"},
        {"name": "Migraine without Aura", "icd10": "G43.909"},
    ]
}

MEDICATIONS = {
    "cardiac": ["Lisinopril 10mg QD", "Metoprolol 50mg BID", "Atorvastatin 40mg QHS", 
                "Aspirin 81mg QD", "Clopidogrel 75mg QD"],
    "diabetes": ["Metformin 1000mg BID", "Glipizide 5mg BID", "Jardiance 25mg QD",
                 "Ozempic 1mg weekly", "Lantus 20 units QHS"],
    "hypertension": ["Amlodipine 5mg QD", "Losartan 50mg QD", "Hydrochlorothiazide 25mg QD",
                     "Lisinopril 20mg QD"],
    "general": ["Omeprazole 20mg QD", "Vitamin D3 2000IU QD", "Cetirizine 10mg QD",
                "Ibuprofen 400mg PRN"]
}

SURGERIES = [
    "Appendectomy", "Cholecystectomy", "Coronary Artery Bypass Graft (CABG)",
    "Total Knee Replacement", "Percutaneous Coronary Intervention (PCI)",
    "Cataract Surgery", "Hernia Repair", "Tonsillectomy", "Cardiac Catheterization"
]

LAB_TEMPLATES = {
    "high_risk_cardiac": {
        "LVEF": lambda: f"{random.randint(25, 40)}%",
        "Troponin": lambda: f"{random.uniform(0.5, 5.0):.2f} ng/mL (elevated)",
        "BNP": lambda: f"{random.randint(500, 2000)} pg/mL",
        "LDL": lambda: f"{random.randint(130, 200)} mg/dL",
        "HbA1c": lambda: f"{random.uniform(7.5, 10.0):.1f}%"
    },
    "medium_risk_diabetic": {
        "HbA1c": lambda: f"{random.uniform(7.0, 8.5):.1f}%",
        "Fasting Glucose": lambda: f"{random.randint(130, 180)} mg/dL",
        "GFR": lambda: f"{random.randint(45, 60)} mL/min",
        "Creatinine": lambda: f"{random.uniform(1.2, 1.8):.1f} mg/dL",
        "Microalbumin": lambda: f"{random.randint(30, 100)} mg/L"
    },
    "low_risk": {
        "HbA1c": lambda: f"{random.uniform(5.0, 5.6):.1f}%",
        "Fasting Glucose": lambda: f"{random.randint(80, 100)} mg/dL",
        "GFR": lambda: f"{random.randint(90, 120)} mL/min",
        "LDL": lambda: f"{random.randint(80, 120)} mg/dL",
        "LVEF": lambda: f"{random.randint(55, 65)}%"
    }
}


class SyntheticDataGenerator:
    """Generates realistic synthetic medical documents."""
    
    def __init__(self, seed: Optional[int] = None):
        self.fake = Faker()
        if seed:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_patient_info(self) -> dict:
        """Generate realistic patient demographics."""
        gender = random.choice(["Male", "Female"])
        first_name = self.fake.first_name_male() if gender == "Male" else self.fake.first_name_female()
        last_name = self.fake.last_name()
        
        return {
            "name": f"{first_name} {last_name}",
            "dob": self.fake.date_of_birth(minimum_age=30, maximum_age=75).strftime("%m/%d/%Y"),
            "gender": gender,
            "mrn": f"MRN-{random.randint(100000, 999999)}",
            "ssn_last4": f"XXX-XX-{random.randint(1000, 9999)}"
        }
    
    def generate_report(self, risk_profile: str = "random") -> tuple[str, str, str]:
        """
        Generate a complete synthetic medical report.
        
        Returns:
            Tuple of (report_text, patient_name, risk_level)
        """
        if risk_profile == "random":
            risk_profile = random.choices(
                ["high_risk", "medium_risk", "low_risk"],
                weights=[0.15, 0.35, 0.50]  # Realistic distribution
            )[0]
        
        patient = self.generate_patient_info()
        conditions = self._select_conditions(risk_profile)
        medications = self._select_medications(conditions)
        labs = self._generate_labs(risk_profile)
        social_history = self._generate_social_history(risk_profile)
        surgical_history = self._generate_surgical_history()
        
        report = self._format_report(
            patient, conditions, medications, labs, 
            social_history, surgical_history, risk_profile
        )
        
        return report, patient["name"].replace(" ", "_"), risk_profile.upper().replace("_", " ")
    
    def _select_conditions(self, risk_profile: str) -> list:
        """Select appropriate conditions based on risk profile."""
        profile_conditions = CONDITIONS.get(risk_profile, CONDITIONS["low_risk"])
        num_conditions = {
            "high_risk": random.randint(2, 4),
            "medium_risk": random.randint(1, 3),
            "low_risk": random.randint(0, 2)
        }.get(risk_profile, 1)
        
        selected = random.sample(profile_conditions, min(num_conditions, len(profile_conditions)))
        
        # Add onset dates
        for condition in selected:
            years_ago = random.randint(1, 10)
            condition["onset"] = (datetime.now() - timedelta(days=years_ago*365)).strftime("%Y")
        
        return selected
    
    def _select_medications(self, conditions: list) -> list:
        """Select appropriate medications based on conditions."""
        meds = []
        condition_names = [c["name"].lower() for c in conditions]
        
        if any("cardiac" in c or "myocardial" in c or "cardiomyopathy" in c for c in condition_names):
            meds.extend(random.sample(MEDICATIONS["cardiac"], random.randint(2, 4)))
        
        if any("diabetes" in c for c in condition_names):
            meds.extend(random.sample(MEDICATIONS["diabetes"], random.randint(2, 3)))
        
        if any("hypertension" in c for c in condition_names):
            meds.extend(random.sample(MEDICATIONS["hypertension"], random.randint(1, 2)))
        
        if not meds:
            meds = random.sample(MEDICATIONS["general"], random.randint(1, 3))
        
        return list(set(meds))[:8]  # Dedupe and limit
    
    def _generate_labs(self, risk_profile: str) -> dict:
        """Generate lab values appropriate to risk profile."""
        if risk_profile == "high_risk":
            template = random.choice([LAB_TEMPLATES["high_risk_cardiac"]])
        elif risk_profile == "medium_risk":
            template = LAB_TEMPLATES["medium_risk_diabetic"]
        else:
            template = LAB_TEMPLATES["low_risk"]
        
        return {key: func() for key, func in template.items()}
    
    def _generate_social_history(self, risk_profile: str) -> dict:
        """Generate social history based on risk profile."""
        tobacco_options = {
            "high_risk": ["Current smoker (1 PPD x 20 years)", "Former smoker (quit 2 years ago)", "Current smoker (2 PPD)"],
            "medium_risk": ["Former smoker (quit 5 years ago)", "Occasional cigar smoker", "Never smoker"],
            "low_risk": ["Never smoker", "Never smoker", "Never used tobacco"]
        }
        
        alcohol_options = {
            "high_risk": ["Heavy alcohol use (6+ drinks/day)", "History of alcohol abuse", "Moderate (2-3 drinks/day)"],
            "medium_risk": ["Moderate (1-2 drinks/day)", "Social drinker (weekends)", "Occasional wine with dinner"],
            "low_risk": ["Occasional social drinker", "Rare alcohol use", "Non-drinker"]
        }
        
        return {
            "tobacco": random.choice(tobacco_options.get(risk_profile, tobacco_options["low_risk"])),
            "alcohol": random.choice(alcohol_options.get(risk_profile, alcohol_options["low_risk"])),
            "occupation": self.fake.job(),
            "exercise": random.choice(["Sedentary", "Light activity", "Moderate exercise 3x/week", "Regular exercise 5x/week"])
        }
    
    def _generate_surgical_history(self) -> list:
        """Generate surgical history."""
        if random.random() < 0.3:
            return ["None reported"]
        
        num_surgeries = random.randint(1, 3)
        surgeries = []
        for _ in range(num_surgeries):
            surgery = random.choice(SURGERIES)
            year = random.randint(2010, 2024)
            surgeries.append(f"{surgery} ({year})")
        
        return surgeries
    
    def _format_report(self, patient: dict, conditions: list, medications: list,
                       labs: dict, social: dict, surgeries: list, risk_profile: str) -> str:
        """Format the complete medical report."""
        
        report_date = datetime.now().strftime("%B %d, %Y")
        physician = self.fake.name()
        clinic = f"{self.fake.city()} {random.choice(['Medical Center', 'Healthcare Associates', 'Internal Medicine', 'Cardiology Group'])}"
        
        conditions_text = "\n".join([
            f"  - {c['name']} (ICD-10: {c['icd10']}) - Diagnosed {c['onset']}"
            for c in conditions
        ]) if conditions else "  - No significant chronic conditions"
        
        meds_text = "\n".join([f"  - {m}" for m in medications]) if medications else "  - No current medications"
        
        labs_text = "\n".join([f"  - {k}: {v}" for k, v in labs.items()])
        
        surgeries_text = "\n".join([f"  - {s}" for s in surgeries])
        
        # Generate clinical narrative
        narratives = {
            "high_risk": f"""
Patient presents for comprehensive evaluation following recent cardiac event.
History significant for progressive symptoms over the past 6 months including
exertional dyspnea, fatigue, and occasional chest discomfort. Recent echocardiogram
demonstrates reduced ejection fraction. Patient has multiple cardiovascular risk factors
including {"diabetes" if any("diabetes" in c["name"].lower() for c in conditions) else "hypertension"}.
Compliance with medication regimen has been suboptimal due to reported side effects.
Recommend close follow-up and specialist referral for optimization of medical therapy.
""",
            "medium_risk": f"""
Patient presents for routine follow-up of chronic conditions. Overall stable clinical status
with well-controlled symptoms on current medication regimen. Labs demonstrate adequate
but not optimal control of metabolic parameters. Patient reports good medication compliance
with occasional missed doses. Lifestyle modifications discussed including diet and exercise.
Continue current management with plan for lab reassessment in 3 months.
""",
            "low_risk": f"""
Patient presents for annual wellness examination. Reports feeling well with no new complaints.
No significant changes in medical history since last visit. Labs within normal limits.
Active lifestyle maintained with regular exercise and healthy diet. No tobacco or excessive
alcohol use. Preventive care up to date including age-appropriate cancer screenings.
Continue current health maintenance plan.
"""
        }
        
        narrative = narratives.get(risk_profile, narratives["low_risk"])
        
        report = f"""
================================================================================
                    ATTENDING PHYSICIAN STATEMENT (APS)
                    Life Insurance Medical Evaluation
================================================================================

REPORT DATE: {report_date}
DOCUMENT ID: APS-{random.randint(100000, 999999)}

--------------------------------------------------------------------------------
PATIENT INFORMATION
--------------------------------------------------------------------------------
Patient Name:     {patient['name']}
Date of Birth:    {patient['dob']}
Gender:           {patient['gender']}
Medical Record #: {patient['mrn']}
SSN (last 4):     {patient['ssn_last4']}

--------------------------------------------------------------------------------
EXAMINING PHYSICIAN
--------------------------------------------------------------------------------
Physician Name:   {physician}, MD
Practice:         {clinic}
NPI:              {random.randint(1000000000, 9999999999)}

--------------------------------------------------------------------------------
CHIEF COMPLAINT / REASON FOR EVALUATION
--------------------------------------------------------------------------------
Life Insurance Medical Evaluation - Comprehensive Health Assessment

--------------------------------------------------------------------------------
CLINICAL NARRATIVE
--------------------------------------------------------------------------------
{narrative.strip()}

--------------------------------------------------------------------------------
ACTIVE MEDICAL CONDITIONS
--------------------------------------------------------------------------------
{conditions_text}

--------------------------------------------------------------------------------
CURRENT MEDICATIONS
--------------------------------------------------------------------------------
{meds_text}

--------------------------------------------------------------------------------
SURGICAL HISTORY
--------------------------------------------------------------------------------
{surgeries_text}

--------------------------------------------------------------------------------
SOCIAL HISTORY
--------------------------------------------------------------------------------
  Tobacco Use:    {social['tobacco']}
  Alcohol Use:    {social['alcohol']}
  Occupation:     {social['occupation']}
  Exercise:       {social['exercise']}

--------------------------------------------------------------------------------
RECENT LABORATORY VALUES
--------------------------------------------------------------------------------
{labs_text}

--------------------------------------------------------------------------------
PHYSICAL EXAMINATION FINDINGS
--------------------------------------------------------------------------------
  Vital Signs:
    - Blood Pressure: {random.randint(110, 150)}/{random.randint(70, 95)} mmHg
    - Heart Rate: {random.randint(60, 100)} bpm
    - Respiratory Rate: {random.randint(14, 20)} breaths/min
    - Temperature: {random.uniform(97.5, 99.0):.1f}°F
    - Height: {random.randint(60, 76)} inches
    - Weight: {random.randint(130, 280)} lbs
    - BMI: {random.uniform(20, 38):.1f}

  General: Patient appears stated age, {"well-nourished" if risk_profile == "low_risk" else "mildly fatigued"}
  HEENT: Normocephalic, atraumatic. Pupils equal and reactive.
  Cardiovascular: {"Regular rate and rhythm, no murmurs" if risk_profile != "high_risk" else "Irregular rhythm, Grade II/VI systolic murmur"}
  Respiratory: {"Clear to auscultation bilaterally" if risk_profile != "high_risk" else "Mild bibasilar crackles"}
  Abdomen: Soft, non-tender, no organomegaly
  Extremities: {"No edema, pulses intact" if risk_profile != "high_risk" else "Trace bilateral lower extremity edema"}

--------------------------------------------------------------------------------
ASSESSMENT AND PLAN
--------------------------------------------------------------------------------
Overall Risk Assessment: {risk_profile.upper().replace('_', ' ')}

This patient {"presents significant underwriting considerations due to recent cardiac history and suboptimal metabolic control" if risk_profile == "high_risk" else "presents moderate risk factors requiring careful consideration" if risk_profile == "medium_risk" else "appears to be a standard risk candidate with no significant health concerns"}.

Recommendations:
{"- Specialist consultation recommended prior to coverage determination" if risk_profile == "high_risk" else "- Standard underwriting process may proceed" if risk_profile == "low_risk" else "- Additional documentation may be required for rating"}

--------------------------------------------------------------------------------
PHYSICIAN ATTESTATION
--------------------------------------------------------------------------------
I certify that the information provided in this Attending Physician Statement
is accurate and complete to the best of my knowledge based on medical records
and examination of the above-named patient.

Signature: [ELECTRONICALLY SIGNED]
{physician}, MD
Date: {report_date}

================================================================================
                         END OF ATTENDING PHYSICIAN STATEMENT
================================================================================

[APPENDIX A - Extended Clinical Notes]
{self.fake.paragraph(nb_sentences=10)}

{self.fake.paragraph(nb_sentences=8)}

{self.fake.paragraph(nb_sentences=12)}

[APPENDIX B - Historical Laboratory Trends]
{self.fake.paragraph(nb_sentences=6)}

================================================================================
"""
        return report


def main():
    """Main entry point for the synthetic data generator."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic medical documents for LifeProof AI testing"
    )
    parser.add_argument(
        "--count", type=int, default=10,
        help="Number of documents to generate (default: 10)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Local output directory for generated files"
    )
    parser.add_argument(
        "--bucket", type=str, default=None,
        help="S3 bucket name for uploading files"
    )
    parser.add_argument(
        "--prefix", type=str, default="uploads/",
        help="S3 key prefix (default: uploads/)"
    )
    parser.add_argument(
        "--profile", type=str, default="random",
        choices=["random", "high_risk", "medium_risk", "low_risk"],
        help="Risk profile for generated documents"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    if not HAS_DEPS:
        print("ERROR: Required dependencies not installed.")
        print("Run: pip install boto3 faker")
        sys.exit(1)
    
    if not args.output and not args.bucket:
        print("ERROR: Must specify either --output (local) or --bucket (S3)")
        sys.exit(1)
    
    generator = SyntheticDataGenerator(seed=args.seed)
    
    # Setup S3 client if needed
    s3_client = None
    if args.bucket:
        s3_client = boto3.client("s3")
    
    # Setup local output if needed
    if args.output:
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🏥 LifeProof AI - Synthetic Data Generator")
    print(f"   Generating {args.count} medical documents...")
    print(f"   Risk Profile: {args.profile}")
    print()
    
    stats = {"high_risk": 0, "medium_risk": 0, "low_risk": 0}
    
    for i in range(args.count):
        report_text, patient_name, risk_level = generator.generate_report(args.profile)
        filename = f"APS_{patient_name}_{i:05d}.txt"
        
        # Track statistics
        risk_key = risk_level.lower().replace(" ", "_")
        if risk_key in stats:
            stats[risk_key] += 1
        
        # Save locally
        if args.output:
            filepath = output_path / filename
            filepath.write_text(report_text)
        
        # Upload to S3
        if args.bucket:
            key = f"{args.prefix}{filename}"
            s3_client.put_object(
                Bucket=args.bucket,
                Key=key,
                Body=report_text,
                ContentType="text/plain"
            )
        
        if (i + 1) % 100 == 0 or i == 0:
            print(f"   ✅ Generated {i + 1}/{args.count} documents...")
    
    print()
    print(f"✨ Generation complete!")
    print(f"   Risk Distribution:")
    print(f"   - High Risk:   {stats['high_risk']} ({100*stats['high_risk']/args.count:.1f}%)")
    print(f"   - Medium Risk: {stats['medium_risk']} ({100*stats['medium_risk']/args.count:.1f}%)")
    print(f"   - Low Risk:    {stats['low_risk']} ({100*stats['low_risk']/args.count:.1f}%)")
    
    if args.output:
        print(f"   Output Directory: {args.output}")
    if args.bucket:
        print(f"   S3 Bucket: s3://{args.bucket}/{args.prefix}")


if __name__ == "__main__":
    main()
