# 🚀 LifeProof AI - POC Quick Start Guide

This guide walks you through deploying and testing the Proof of Concept using **Claude 3.5 Haiku**.

## Prerequisites

1. **AWS CLI** configured with your credentials
2. **AWS CDK CLI** installed: `npm install -g aws-cdk`
3. **Python 3.12+**
4. **Amazon Bedrock access** to Claude 3.5 Haiku enabled in your region

### Enable Bedrock Model Access

1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable **Claude 3.5 Haiku** from Anthropic
5. Click **Save changes**

## Step 1: Setup Environment

```bash
# Navigate to project directory
cd lifeproof-ai

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap
```

## Step 2: Deploy POC Stack

```bash
# Deploy the POC stack (uses Haiku only)
cdk deploy --app "python app_poc.py"

# Confirm the deployment when prompted
```

**Expected Resources:**
- 1 S3 Bucket (for documents and summaries)
- 1 Lambda Function (with Haiku)
- 1 Step Function
- 1 DynamoDB Table

**Estimated Cost:** < $1/day for light testing

## Step 3: Run the Test

### Option A: Using the Test Runner Script

```bash
# Run the complete test flow
python scripts/run_poc.py --stack-name LifeProofAiPoc

# This will:
# 1. Upload 3 sample documents (LOW, MEDIUM, HIGH risk)
# 2. Start the Step Function
# 3. Wait for completion
# 4. Display results
```

### Option B: Test Lambda Directly

```bash
# Test Lambda function directly (faster, good for debugging)
python scripts/run_poc.py --stack-name LifeProofAiPoc --direct
```

### Option C: Manual Testing via AWS Console

1. **Upload a document:**
   ```bash
   # Get bucket name from stack outputs
   BUCKET=$(aws cloudformation describe-stacks \
     --stack-name LifeProofAiPoc \
     --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
     --output text)
   
   # Upload sample document
   aws s3 cp sample_documents/APS_LOW_RISK_Sarah_Johnson.txt \
     s3://$BUCKET/uploads/
   ```

2. **Start Step Function:**
   ```bash
   STATE_MACHINE=$(aws cloudformation describe-stacks \
     --stack-name LifeProofAiPoc \
     --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
     --output text)
   
   aws stepfunctions start-execution \
     --state-machine-arn $STATE_MACHINE \
     --input '{
       "documents": [
         {"bucket": "'$BUCKET'", "key": "uploads/APS_LOW_RISK_Sarah_Johnson.txt"}
       ]
     }'
   ```

3. **Check Results:**
   ```bash
   # List summaries
   aws s3 ls s3://$BUCKET/summaries/
   
   # View a summary
   aws s3 cp s3://$BUCKET/summaries/APS_LOW_RISK_Sarah_Johnson_summary.json -
   ```

## Step 4: View Results

```bash
# View all results (summaries and tracking data)
python scripts/run_poc.py --stack-name LifeProofAiPoc --view-results
```

### Expected Output

For each document, you'll see a JSON summary like:

```json
{
  "patient_name": "Sarah Johnson",
  "risk_level": "LOW",
  "conditions": ["Seasonal allergies", "Vitamin D insufficiency"],
  "medications": ["Cetirizine 10mg", "Vitamin D3 2000 IU"],
  "risk_factors": [],
  "lifestyle": {
    "tobacco": "never",
    "alcohol": "moderate"
  },
  "summary": "Healthy 40-year-old female with no significant medical conditions..."
}
```

## Step 5: Cleanup

```bash
# Clean up test files (keeps the stack)
python scripts/run_poc.py --stack-name LifeProofAiPoc --cleanup

# OR destroy the entire stack
cdk destroy --app "python app_poc.py"
```

## Sample Documents Included

| File | Risk Level | Key Conditions |
|------|------------|----------------|
| `APS_LOW_RISK_Sarah_Johnson.txt` | LOW | Healthy, no chronic conditions |
| `APS_MEDIUM_RISK_Robert_Martinez.txt` | MEDIUM | Type 2 Diabetes, Hypertension, Former smoker |
| `APS_HIGH_RISK_James_Wilson.txt` | HIGH | Recent MI, LVEF 40%, Current smoker, Poor diabetes control |

## Troubleshooting

### "Model not available" error
- Ensure Claude 3.5 Haiku is enabled in Bedrock console
- Check you're deploying to a region where Bedrock is available (us-east-1, us-west-2, etc.)

### Lambda timeout
- Increase timeout in `infrastructure/poc_stack.py` if processing large documents
- Current default: 60 seconds

### Permission denied
- Ensure your AWS credentials have permissions for:
  - CloudFormation
  - S3
  - Lambda
  - Step Functions
  - DynamoDB
  - Bedrock

## Next Steps

After validating the POC:

1. **Scale Up**: Deploy the full stack with `cdk deploy` (uses intelligent model routing)
2. **Add More Documents**: Use `scripts/gen_synthetic_data.py` to generate test data
3. **Customize Prompts**: Modify the underwriting rubric in `lambda/summarizer/index.py`
4. **Enable Monitoring**: Add CloudWatch dashboards and alarms

---

**Questions?** Check the main [README.md](README.md) for full documentation.
