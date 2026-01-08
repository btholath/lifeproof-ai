#!/usr/bin/env python3
"""
LifeProof AI - Prompt Regression Testing Framework

This script validates prompt changes before deployment by comparing new AI summaries
against a "Gold Standard" set of human-validated cases using an LLM-as-a-Judge approach.

Features:
- Automated regression testing across gold standard cases
- LLM-as-a-Judge evaluation using Claude
- Detailed scoring and reporting
- CI/CD integration support

Usage:
    # Run regression test against gold standard
    python prompt_regression_test.py --gold-standard ./gold_standard.jsonl
    
    # Run with specific prompt version
    python prompt_regression_test.py --gold-standard ./gold_standard.jsonl --prompt-version v2.1
    
    # Output results to JSON
    python prompt_regression_test.py --gold-standard ./gold_standard.jsonl --output results.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# ============================================================
# EVALUATION CONFIGURATION
# ============================================================

JUDGE_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
GENERATOR_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

# Minimum passing score (out of 5)
PASSING_THRESHOLD = 4.0

# Critical failure - any score of 1 fails the test
CRITICAL_FAILURE_SCORE = 1


JUDGE_PROMPT = """
You are a Senior Underwriting Auditor validating AI-generated medical summaries for a Life Insurance company.

Your task is to compare an AI-generated summary against a human-validated "Gold Standard" summary and score the AI's performance.

## Evaluation Criteria

Score each category from 1-5:

### 1. FACTUAL ACCURACY (Critical)
- 5: All facts match the original document perfectly
- 4: Minor omissions that don't affect underwriting decision
- 3: Some inaccuracies in non-critical details
- 2: Significant inaccuracies present
- 1: CRITICAL ERROR - Major facts wrong or fabricated (hallucination)

### 2. RISK ALIGNMENT (Critical)
- 5: Risk level matches human assessment exactly
- 4: Risk level matches, minor differences in reasoning
- 3: Risk level off by one category with valid reasoning
- 2: Risk level misaligned without clear justification
- 1: CRITICAL ERROR - High risk flagged as Low or vice versa

### 3. COMPLETENESS
- 5: All relevant information captured
- 4: Minor details missing, all critical items present
- 3: Some relevant information missing
- 2: Significant gaps in coverage
- 1: Major categories completely missing

### 4. CLINICAL RELEVANCE
- 5: Summary focuses on underwriting-relevant details
- 4: Good focus with minor irrelevant inclusions
- 3: Mix of relevant and irrelevant information
- 2: Too much irrelevant detail obscures key findings
- 1: Fails to highlight critical underwriting concerns

### 5. ACTIONABILITY
- 5: Underwriter can make decision without original document
- 4: Underwriter can make decision with minor clarifications
- 3: Underwriter needs to review some sections of original
- 2: Significant review of original required
- 1: Summary is not useful for decision-making

## Scoring Rules
- ANY score of 1 in categories 1 or 2 = AUTOMATIC FAILURE
- Average score below 4.0 = NEEDS IMPROVEMENT
- Average score 4.0+ = PASSING

<human_gold_standard>
{human_summary}
</human_gold_standard>

<ai_generated_summary>
{ai_summary}
</ai_generated_summary>

Provide your evaluation in the following JSON format ONLY:
{{
  "factual_accuracy": {{"score": X, "notes": "..."}},
  "risk_alignment": {{"score": X, "notes": "..."}},
  "completeness": {{"score": X, "notes": "..."}},
  "clinical_relevance": {{"score": X, "notes": "..."}},
  "actionability": {{"score": X, "notes": "..."}},
  "average_score": X.X,
  "critical_failure": true/false,
  "overall_verdict": "PASS" | "FAIL" | "NEEDS_REVIEW",
  "summary_feedback": "Brief overall assessment"
}}
"""


class PromptRegressionTester:
    """Manages prompt regression testing workflow."""
    
    def __init__(self, prompt_version: str = "default"):
        self.bedrock = boto3.client("bedrock-runtime")
        self.prompt_version = prompt_version
        self.results = []
    
    def load_gold_standard(self, filepath: str) -> list:
        """Load gold standard test cases from JSONL file."""
        cases = []
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Gold standard file not found: {filepath}")
        
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
        
        return cases
    
    def generate_summary(self, input_text: str) -> str:
        """Generate a new summary using the current prompt version."""
        # This would use the same prompt as the Lambda function
        # For testing, we import the prompt from the Lambda module
        from lambda_summarizer_prompt import UNDERWRITING_RUBRIC, OUTPUT_SCHEMA
        
        prompt = f"""
{UNDERWRITING_RUBRIC}

<medical_document>
{input_text}
</medical_document>

Required output format:
{OUTPUT_SCHEMA}

Return ONLY the JSON object.
"""
        
        try:
            response = self.bedrock.invoke_model(
                modelId=GENERATOR_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]
            
        except ClientError as e:
            print(f"ERROR: Bedrock invocation failed: {e}")
            raise
    
    def evaluate_summary(self, ai_summary: str, human_summary: str) -> dict:
        """Use LLM-as-a-Judge to evaluate the AI summary."""
        judge_prompt = JUDGE_PROMPT.format(
            human_summary=human_summary,
            ai_summary=ai_summary
        )
        
        try:
            response = self.bedrock.invoke_model(
                modelId=JUDGE_MODEL,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": judge_prompt}]
                })
            )
            
            response_body = json.loads(response["body"].read())
            eval_text = response_body["content"][0]["text"]
            
            # Parse JSON from response
            eval_text = eval_text.strip()
            if eval_text.startswith("```json"):
                eval_text = eval_text[7:]
            if eval_text.startswith("```"):
                eval_text = eval_text[3:]
            if eval_text.endswith("```"):
                eval_text = eval_text[:-3]
            
            return json.loads(eval_text.strip())
            
        except Exception as e:
            print(f"ERROR: Evaluation failed: {e}")
            return {
                "error": str(e),
                "overall_verdict": "ERROR",
                "average_score": 0
            }
    
    def run_test(self, case: dict) -> dict:
        """Run a single test case."""
        case_id = case.get("case_id", "unknown")
        input_text = case.get("input_text", "")
        human_summary = case.get("human_summary", "")
        
        print(f"  Testing case: {case_id}...")
        
        # Generate new summary
        ai_summary = self.generate_summary(input_text)
        
        # Evaluate against gold standard
        evaluation = self.evaluate_summary(ai_summary, human_summary)
        
        result = {
            "case_id": case_id,
            "prompt_version": self.prompt_version,
            "timestamp": datetime.utcnow().isoformat(),
            "evaluation": evaluation,
            "ai_summary": ai_summary[:500] + "..." if len(ai_summary) > 500 else ai_summary
        }
        
        self.results.append(result)
        return result
    
    def run_all_tests(self, gold_standard_path: str) -> dict:
        """Run all test cases and generate summary report."""
        print(f"\n🧪 LifeProof AI - Prompt Regression Testing")
        print(f"   Prompt Version: {self.prompt_version}")
        print(f"   Gold Standard: {gold_standard_path}")
        print()
        
        cases = self.load_gold_standard(gold_standard_path)
        print(f"   Loaded {len(cases)} test cases")
        print()
        
        passed = 0
        failed = 0
        errors = 0
        critical_failures = []
        
        for case in cases:
            result = self.run_test(case)
            verdict = result["evaluation"].get("overall_verdict", "ERROR")
            
            if verdict == "PASS":
                passed += 1
                print(f"    ✅ {result['case_id']}: PASS")
            elif verdict == "ERROR":
                errors += 1
                print(f"    ⚠️ {result['case_id']}: ERROR")
            else:
                failed += 1
                print(f"    ❌ {result['case_id']}: FAIL")
                
                if result["evaluation"].get("critical_failure"):
                    critical_failures.append(result["case_id"])
        
        print()
        print("=" * 60)
        print("REGRESSION TEST SUMMARY")
        print("=" * 60)
        print(f"  Total Cases:      {len(cases)}")
        print(f"  Passed:           {passed} ({100*passed/len(cases):.1f}%)")
        print(f"  Failed:           {failed} ({100*failed/len(cases):.1f}%)")
        print(f"  Errors:           {errors}")
        print()
        
        if critical_failures:
            print(f"  ⛔ CRITICAL FAILURES: {critical_failures}")
            print("     These cases had major accuracy or risk alignment errors!")
        
        # Calculate average scores
        scores = [r["evaluation"].get("average_score", 0) for r in self.results if "average_score" in r.get("evaluation", {})]
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"  Average Score:    {avg_score:.2f}/5.0")
        
        overall_pass = passed == len(cases) and not critical_failures
        print()
        if overall_pass:
            print("  🎉 REGRESSION TEST PASSED - Ready for deployment")
        else:
            print("  ❌ REGRESSION TEST FAILED - Do not deploy")
        
        return {
            "prompt_version": self.prompt_version,
            "timestamp": datetime.utcnow().isoformat(),
            "total_cases": len(cases),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "critical_failures": critical_failures,
            "average_score": sum(scores) / len(scores) if scores else 0,
            "overall_pass": overall_pass,
            "results": self.results
        }


def create_sample_gold_standard(output_path: str):
    """Create a sample gold standard file for demonstration."""
    sample_cases = [
        {
            "case_id": "GOLD-001",
            "input_text": """
ATTENDING PHYSICIAN STATEMENT
Patient: John Doe | DOB: 05/12/1978
Clinical Narrative: Patient presented with history of Type 2 Diabetes diagnosed 2018.
Current HbA1c: 7.4%. Medications: Metformin 1000mg BID.
Social History: Never smoker, occasional alcohol.
Assessment: Well-controlled diabetes on monotherapy.
            """,
            "human_summary": json.dumps({
                "risk_level": "MEDIUM",
                "conditions": [{"name": "Type 2 Diabetes Mellitus", "onset_date": "2018", "status": "managed"}],
                "medications": [{"name": "Metformin", "dosage": "1000mg BID", "compliance": "compliant"}],
                "lifestyle_flags": {"tobacco": "never", "alcohol": "moderate"},
                "lab_values": {"HbA1c": "7.4%"},
                "underwriter_notes": "Well-controlled T2DM on monotherapy, standard risk considerations apply"
            })
        },
        {
            "case_id": "GOLD-002",
            "input_text": """
ATTENDING PHYSICIAN STATEMENT
Patient: Jane Smith | DOB: 03/15/1960
Clinical Narrative: History of MI (STEMI) in 2022. Current LVEF 42%.
Medications: Lisinopril 20mg, Metoprolol 50mg, Atorvastatin 80mg, Aspirin 81mg.
Social History: Former smoker (quit post-MI), no alcohol.
Recent echo shows stable but reduced function.
            """,
            "human_summary": json.dumps({
                "risk_level": "HIGH",
                "conditions": [{"name": "Myocardial Infarction (STEMI)", "onset_date": "2022", "status": "managed"}],
                "medications": [
                    {"name": "Lisinopril", "dosage": "20mg", "compliance": "compliant"},
                    {"name": "Metoprolol", "dosage": "50mg", "compliance": "compliant"},
                    {"name": "Atorvastatin", "dosage": "80mg", "compliance": "compliant"},
                    {"name": "Aspirin", "dosage": "81mg", "compliance": "compliant"}
                ],
                "lifestyle_flags": {"tobacco": "former", "alcohol": "none"},
                "lab_values": {"LVEF": "42%"},
                "underwriter_notes": "Recent MI with reduced EF <45%, HIGH risk per rubric"
            })
        }
    ]
    
    with open(output_path, "w") as f:
        for case in sample_cases:
            f.write(json.dumps(case) + "\n")
    
    print(f"Created sample gold standard file: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="LifeProof AI Prompt Regression Testing"
    )
    parser.add_argument(
        "--gold-standard", type=str,
        help="Path to gold standard JSONL file"
    )
    parser.add_argument(
        "--prompt-version", type=str, default="default",
        help="Prompt version identifier"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output path for results JSON"
    )
    parser.add_argument(
        "--create-sample", type=str, default=None,
        help="Create a sample gold standard file at the specified path"
    )
    
    args = parser.parse_args()
    
    if not HAS_DEPS:
        print("ERROR: Required dependencies not installed.")
        print("Run: pip install boto3")
        sys.exit(1)
    
    if args.create_sample:
        create_sample_gold_standard(args.create_sample)
        return
    
    if not args.gold_standard:
        print("ERROR: --gold-standard path required")
        print("Use --create-sample to generate a sample file")
        sys.exit(1)
    
    tester = PromptRegressionTester(prompt_version=args.prompt_version)
    results = tester.run_all_tests(args.gold_standard)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit with appropriate code for CI/CD
    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()
