"""
The AI Logic
This function handles the extraction, model routing, and storage.
"""
import json
import os

import boto3

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')


def handler(event, context):
    # 1. Get metadata from the Step Function event
    bucket = event['Bucket']
    key = event['Key']

    # 2. Download and Extract (Simplified for POC)
    obj = s3.get_object(Bucket=bucket, Key=key)
    text = obj['Body'].read().decode('utf-8')

    # 3. Bedrock Multi-Model Routing logic
    # Use Sonnet for long reports, Haiku for short ones
    model_id = 'anthropic.claude-3-haiku-20240307-v1:0' if len(
        text) < 10000 else 'anthropic.claude-3-5-sonnet-20240620-v1:0'

    prompt = f"Summarize this medical report for an insurance underwriter: {text[:5000]}"

    response = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    summary = json.loads(response['body'].read())['content'][0]['text']

    # 4. Save to Summary Bucket
    output_key = f"summaries/{key.split('/')[-1]}.json"
    s3.put_object(
        Bucket=os.environ['SUMMARY_BUCKET'],
        Key=output_key,
        Body=json.dumps({"original_file": key, "summary": summary})
    )

    return {"status": "SUCCEEDED", "key": output_key}
