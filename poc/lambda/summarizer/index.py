"""
LifeProof AI - Medical Document Summarizer Lambda

This Lambda function performs AI-powered summarization of medical documents
(Attending Physician Statements, medical examination reports) for life insurance
underwriting purposes.

Features:
- Intelligent model routing (Sonnet for complex, Haiku for simple)
- Structured output with risk classification
- Chain-of-Thought prompting for clinical accuracy
- Comprehensive error handling and audit logging
- DynamoDB tracking for compliance

Author: LifeProof AI Platform Team
"""

import json
import os
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger = logging.getLogger()
logger.setLevel(log_level)

# Initialize AWS clients
s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")

# Environment variables - Support both full stack and POC configurations
SUMMARY_BUCKET = os.environ.get("SUMMARY_BUCKET") or os.environ.get("BUCKET_NAME")
FAILED_BUCKET = os.environ.get("FAILED_BUCKET") or os.environ.get("BUCKET_NAME")
TRACKING_TABLE = os.environ.get("TRACKING_TABLE")

# Model configuration - defaults to Haiku for POC, can use Sonnet for production
MODEL_ID = os.environ.get("MODEL_ID")  # Single model mode (POC)
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "anthropic.claude-3-5-sonnet-20241022-v2:0")
FAST_MODEL = os.environ.get("FAST_MODEL", "anthropic.claude-3-5-haiku-20241022-v1:0")

# Token threshold for model routing (only used if MODEL_ID not set)
TOKEN_THRESHOLD = 8000  # Use faster model for shorter documents

# ============================================================
# UNDERWRITING RUBRIC - The Clinical Risk Classification System
# ============================================================

UNDERWRITING_RUBRIC = """
<underwriting_rubric>
You are an automated Underwriting Assistant for a major Life Insurance provider.
Your task is to extract clinical risk factors from medical documents and classify
the applicant's risk level based on the following STRICT rubric:

## Risk Classification Criteria

### HIGH RISK (Requires Senior Underwriter Review)
- Any history of Myocardial Infarction (MI) or Stroke within the last 5 years
- Left Ventricular Ejection Fraction (LVEF) < 45%
- Active malignancy or cancer treatment within 2 years
- End-stage renal disease (ESRD) or dialysis
- Insulin-dependent diabetes with HbA1c > 9.0%
- Severe COPD (FEV1 < 50% predicted)
- Active substance abuse or addiction
- Organ transplant recipient

### MEDIUM RISK (Standard Review with Conditions)
- Managed Type 2 Diabetes (HbA1c 7.0-9.0%)
- Treated Hypertension requiring 2+ medications
- Current or former tobacco use (within 5 years)
- Controlled Atrial Fibrillation
- Stage 2-3 Chronic Kidney Disease (GFR 30-60)
- History of cancer in remission > 2 years
- Obesity (BMI > 35)
- Sleep apnea on CPAP therapy

### LOW RISK (Standard Approval)
- No chronic conditions
- Stable conditions managed with single-medication therapy
- Controlled hypertension on monotherapy
- Pre-diabetes (HbA1c < 6.5%)
- Minor surgical history (appendectomy, cholecystectomy, etc.)
- Allergies or minor skin conditions

## Required Analysis Steps

1. **Identify Chronic Conditions:** List ALL diagnosed chronic illnesses with date of onset
2. **Medication Analysis:** Extract current prescriptions and note any non-compliance mentions
3. **Lifestyle Assessment:** Flag tobacco use, alcohol abuse, hazardous hobbies
4. **Recent Events:** List hospitalizations or surgeries in the last 24 months
5. **Laboratory Review:** Note any abnormal values (HbA1c, GFR, EF%, cholesterol)
6. **Risk Determination:** Compare findings against the rubric above

## Output Requirements

Return ONLY a valid JSON object. Do not include any explanatory text outside the JSON.
If information is missing for a section, use "Not found in report" - NEVER fabricate data.
</underwriting_rubric>
"""

OUTPUT_SCHEMA = """
{
  "patient_id": "string - Patient identifier from document",
  "processing_id": "string - Unique processing ID",
  "risk_level": "HIGH | MEDIUM | LOW",
  "risk_factors": ["array of identified risk factors"],
  "conditions": [
    {
      "name": "string - condition name",
      "onset_date": "string - date of diagnosis",
      "status": "active | managed | resolved"
    }
  ],
  "medications": [
    {
      "name": "string - medication name",
      "dosage": "string - dosage",
      "compliance": "compliant | non-compliant | unknown"
    }
  ],
  "surgeries": [
    {
      "procedure": "string",
      "date": "string",
      "outcome": "string"
    }
  ],
  "lifestyle_flags": {
    "tobacco": "current | former | never | unknown",
    "alcohol": "none | moderate | heavy | unknown",
    "hazardous_activities": ["array of activities"]
  },
  "lab_values": {
    "HbA1c": "value or Not found",
    "GFR": "value or Not found",
    "LVEF": "value or Not found",
    "LDL": "value or Not found"
  },
  "underwriter_notes": "string - Key observations for human review",
  "confidence_score": "HIGH | MEDIUM | LOW",
  "model_used": "string - Model ID used for summarization"
}
"""


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation based on character count.
    Claude typically uses ~4 characters per token for English text.
    """
    return len(text) // 4


def select_model(text: str) -> str:
    """
    Intelligent model routing based on document complexity.
    
    In POC mode (MODEL_ID env var set): Always use the specified model
    In Production mode: Route based on document length
    - Shorter documents (<8000 tokens): Use Haiku for speed and cost
    - Longer documents (>8000 tokens): Use Sonnet for complex reasoning
    """
    # POC mode - use single specified model
    if MODEL_ID:
        logger.info(f"POC mode: Using specified model {MODEL_ID}")
        return MODEL_ID
    
    # Production mode - intelligent routing
    estimated_tokens = estimate_tokens(text)
    
    if estimated_tokens < TOKEN_THRESHOLD:
        logger.info(f"Routing to FAST model (estimated {estimated_tokens} tokens)")
        return FAST_MODEL
    else:
        logger.info(f"Routing to DEFAULT model (estimated {estimated_tokens} tokens)")
        return DEFAULT_MODEL


def extract_document(bucket: str, key: str) -> str:
    """
    Extract text content from S3 document.
    Supports both TXT and PDF (text-based) files.
    """
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read()
        
        # Handle text files
        if key.endswith(".txt"):
            return content.decode("utf-8")
        
        # Handle PDF (basic text extraction)
        # In production, use Amazon Textract for complex PDFs
        if key.endswith(".pdf"):
            # For this POC, we assume text-based PDFs
            # Real implementation would use Textract
            try:
                return content.decode("utf-8", errors="ignore")
            except Exception:
                logger.warning(f"Could not extract text from PDF: {key}")
                return content.decode("latin-1", errors="ignore")
        
        return content.decode("utf-8", errors="ignore")
        
    except ClientError as e:
        logger.error(f"Error extracting document {bucket}/{key}: {e}")
        raise


def invoke_bedrock(text: str, model_id: str, processing_id: str) -> dict:
    """
    Invoke Amazon Bedrock with the medical summarization prompt.
    Uses Chain-of-Thought prompting for clinical accuracy.
    """
    # Truncate text if too long (preserve first and last portions)
    max_input_chars = 150000  # ~37.5k tokens, safe for 200k context
    if len(text) > max_input_chars:
        half = max_input_chars // 2
        text = text[:half] + "\n\n[...DOCUMENT TRUNCATED...]\n\n" + text[-half:]
        logger.warning("Document truncated due to length")

    user_prompt = f"""
Analyze the following medical document and generate an underwriting summary.

{UNDERWRITING_RUBRIC}

<medical_document>
{text}
</medical_document>

Required output format:
{OUTPUT_SCHEMA}

IMPORTANT: 
- Use processing_id: "{processing_id}"
- model_used: "{model_id}"
- Return ONLY the JSON object, no additional text
- Think step-by-step before determining the risk level
- Cross-reference all findings against the rubric criteria
"""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0,  # Deterministic for compliance
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response["body"].read())
        summary_text = response_body["content"][0]["text"]
        
        # Parse JSON from response (handle markdown code blocks)
        summary_text = summary_text.strip()
        if summary_text.startswith("```json"):
            summary_text = summary_text[7:]
        if summary_text.startswith("```"):
            summary_text = summary_text[3:]
        if summary_text.endswith("```"):
            summary_text = summary_text[:-3]
        
        return json.loads(summary_text.strip())
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response as JSON: {e}")
        # Return a structured error response
        return {
            "processing_id": processing_id,
            "risk_level": "UNKNOWN",
            "error": "Failed to parse AI response",
            "raw_response": summary_text[:1000] if 'summary_text' in locals() else "No response",
            "model_used": model_id
        }
    except ClientError as e:
        logger.error(f"Bedrock invocation failed: {e}")
        raise


def save_summary(summary: dict, original_key: str) -> str:
    """
    Save the generated summary to the output S3 bucket.
    """
    # Generate output key based on original filename
    filename = original_key.split("/")[-1]
    base_name = filename.rsplit(".", 1)[0]
    output_key = f"summaries/{base_name}_summary.json"
    
    summary["original_document"] = original_key
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    
    s3.put_object(
        Bucket=SUMMARY_BUCKET,
        Key=output_key,
        Body=json.dumps(summary, indent=2, default=str),
        ContentType="application/json"
    )
    
    logger.info(f"Summary saved to s3://{SUMMARY_BUCKET}/{output_key}")
    return output_key


def save_failed_document(error_info: dict, original_key: str) -> str:
    """
    Save failed document information to the failed bucket.
    """
    filename = original_key.split("/")[-1]
    base_name = filename.rsplit(".", 1)[0]
    output_key = f"failed/{base_name}_error.json"
    
    error_info["original_document"] = original_key
    error_info["failed_at"] = datetime.now(timezone.utc).isoformat()
    
    s3.put_object(
        Bucket=FAILED_BUCKET,
        Key=output_key,
        Body=json.dumps(error_info, indent=2, default=str),
        ContentType="application/json"
    )
    
    logger.info(f"Error info saved to s3://{FAILED_BUCKET}/{output_key}")
    return output_key


def update_tracking_table(record: dict) -> None:
    """
    Update DynamoDB tracking table for audit trail.
    """
    if not TRACKING_TABLE:
        logger.warning("TRACKING_TABLE not configured, skipping audit log")
        return
    
    try:
        table = dynamodb.Table(TRACKING_TABLE)
        table.put_item(Item=record)
        logger.info(f"Tracking record saved: {record['document_id']}")
    except ClientError as e:
        logger.error(f"Failed to update tracking table: {e}")


def handler(event: dict, context: Any) -> dict:
    """
    Main Lambda handler for medical document summarization.
    
    Supports multiple event formats:
    
    POC format:
    {
        "bucket": "bucket-name",
        "key": "uploads/document.txt"
    }
    
    Production format:
    {
        "Bucket": "bucket-name",
        "Key": "uploads/document.txt"
    }
    """
    logger.info(f"Processing event: {json.dumps(event)}")
    
    # Generate unique processing ID
    processing_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Extract bucket and key - support both formats (POC uses lowercase)
    bucket = event.get("Bucket") or event.get("bucket")
    key = event.get("Key") or event.get("key")
    
    if not bucket or not key:
        error_msg = "Missing required 'Bucket'/'bucket' or 'Key'/'key' in event"
        logger.error(error_msg)
        return {
            "status": "FAILED",
            "error": error_msg,
            "processing_id": processing_id
        }
    
    # Skip non-document files
    if not (key.endswith(".txt") or key.endswith(".pdf")):
        logger.info(f"Skipping non-document file: {key}")
        return {
            "status": "SKIPPED",
            "reason": "Not a supported document type",
            "key": key
        }
    
    try:
        # Step 1: Extract document content
        logger.info(f"Extracting document: s3://{bucket}/{key}")
        document_text = extract_document(bucket, key)
        
        if not document_text.strip():
            raise ValueError("Document is empty or could not be extracted")
        
        # Step 2: Select appropriate model
        model_id = select_model(document_text)
        
        # Step 3: Generate summary using Bedrock
        logger.info(f"Invoking Bedrock model: {model_id}")
        summary = invoke_bedrock(document_text, model_id, processing_id)
        
        # Step 4: Save summary to S3
        output_key = save_summary(summary, key)
        
        # Step 5: Update tracking table
        tracking_record = {
            "document_id": key,
            "processing_timestamp": timestamp,
            "processing_id": processing_id,
            "status": "COMPLETED",
            "risk_level": summary.get("risk_level", "UNKNOWN"),
            "model_used": model_id,
            "summary_location": f"s3://{SUMMARY_BUCKET}/{output_key}",
            "confidence_score": summary.get("confidence_score", "UNKNOWN")
        }
        update_tracking_table(tracking_record)
        
        return {
            "status": "SUCCEEDED",
            "processing_id": processing_id,
            "input_key": key,
            "output_key": output_key,
            "risk_level": summary.get("risk_level", "UNKNOWN"),
            "model_used": model_id
        }
        
    except Exception as e:
        logger.error(f"Processing failed for {key}: {str(e)}", exc_info=True)
        
        # Save error information
        error_info = {
            "processing_id": processing_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "bucket": bucket,
            "key": key
        }
        
        try:
            save_failed_document(error_info, key)
        except Exception as save_error:
            logger.error(f"Failed to save error info: {save_error}")
        
        # Update tracking table with failure
        tracking_record = {
            "document_id": key,
            "processing_timestamp": timestamp,
            "processing_id": processing_id,
            "status": "FAILED",
            "error_message": str(e)[:500],
            "risk_level": "ERROR"
        }
        update_tracking_table(tracking_record)
        
        # Re-raise for Step Function retry handling
        raise
