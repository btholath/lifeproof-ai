"""
LifeProof AI - POC Summarizer Lambda

Simplified Lambda function using Claude 3.5 Haiku for proof of concept.
Focuses on core summarization functionality without complex routing.
"""

import json
import os
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")

# Environment
BUCKET_NAME = os.environ.get("BUCKET_NAME")
TRACKING_TABLE = os.environ.get("TRACKING_TABLE")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")


# ============================================================
# UNDERWRITING PROMPT - Simplified for POC
# ============================================================

PROMPT_TEMPLATE = """You are an expert Medical Underwriter for a Life Insurance company.
Analyze the following medical document and provide a structured risk assessment.

## Risk Classification Rules:
- **HIGH**: MI/Stroke within 5 years, LVEF < 45%, active cancer, ESRD
- **MEDIUM**: Managed diabetes (HbA1c 7-9%), hypertension on 2+ meds, tobacco use
- **LOW**: No chronic conditions, stable conditions on single medication

<medical_document>
{document_text}
</medical_document>

Return your analysis as a JSON object with this exact structure:
{{
  "patient_name": "Name from document",
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "conditions": ["list of diagnosed conditions"],
  "medications": ["list of current medications"],
  "risk_factors": ["key factors affecting risk level"],
  "lifestyle": {{
    "tobacco": "current/former/never",
    "alcohol": "none/moderate/heavy"
  }},
  "summary": "2-3 sentence summary for underwriter"
}}

Return ONLY valid JSON, no additional text."""


def handler(event, context):
    """
    Process a single document and generate an underwriting summary.
    
    Event format:
    {
        "bucket": "bucket-name",
        "key": "uploads/document.txt"
    }
    """
    logger.info(f"Processing: {json.dumps(event)}")
    
    bucket = event.get("bucket", BUCKET_NAME)
    key = event.get("key")
    
    if not key:
        return {"status": "ERROR", "message": "Missing 'key' in event"}
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    try:
        # 1. Get document from S3
        logger.info(f"Fetching: s3://{bucket}/{key}")
        response = s3.get_object(Bucket=bucket, Key=key)
        document_text = response["Body"].read().decode("utf-8")
        
        if not document_text.strip():
            raise ValueError("Document is empty")
        
        # 2. Call Bedrock with Haiku
        logger.info(f"Calling Bedrock model: {MODEL_ID}")
        prompt = PROMPT_TEMPLATE.format(document_text=document_text[:50000])
        
        bedrock_response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(bedrock_response["body"].read())
        summary_text = response_body["content"][0]["text"]
        
        # Parse JSON response
        summary_text = summary_text.strip()
        if summary_text.startswith("```"):
            summary_text = summary_text.split("```")[1]
            if summary_text.startswith("json"):
                summary_text = summary_text[4:]
        
        summary = json.loads(summary_text.strip())
        
        # 3. Save summary to S3
        output_key = key.replace("uploads/", "summaries/").replace(".txt", "_summary.json")
        summary["source_document"] = key
        summary["processed_at"] = timestamp
        summary["model_used"] = MODEL_ID
        
        s3.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=json.dumps(summary, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Saved summary: s3://{bucket}/{output_key}")
        
        # 4. Update tracking table
        if TRACKING_TABLE:
            table = dynamodb.Table(TRACKING_TABLE)
            table.put_item(Item={
                "document_id": key,
                "timestamp": timestamp,
                "status": "COMPLETED",
                "risk_level": summary.get("risk_level", "UNKNOWN"),
                "summary_key": output_key
            })
        
        return {
            "status": "SUCCESS",
            "input": key,
            "output": output_key,
            "risk_level": summary.get("risk_level"),
            "patient_name": summary.get("patient_name")
        }
        
    except Exception as e:
        logger.error(f"Error processing {key}: {str(e)}")
        
        # Track failure
        if TRACKING_TABLE:
            try:
                table = dynamodb.Table(TRACKING_TABLE)
                table.put_item(Item={
                    "document_id": key,
                    "timestamp": timestamp,
                    "status": "FAILED",
                    "error": str(e)[:500]
                })
            except Exception:
                pass
        
        return {
            "status": "ERROR",
            "input": key,
            "error": str(e)
        }
