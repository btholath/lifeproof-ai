# 🏥 LifeProof AI

**High-Scale Medical Document Summarization Pipeline for Life Insurance Underwriting**

[![AWS CDK](https://img.shields.io/badge/AWS%20CDK-2.170+-orange.svg)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-Claude%203.5-purple.svg)](https://aws.amazon.com/bedrock/)

## 📋 Overview

LifeProof AI is an enterprise-grade, serverless pipeline that automates the summarization of medical documents (Attending Physician Statements, medical examination reports) for life insurance underwriting. It leverages Amazon Bedrock's Claude models to generate structured risk assessments, enabling underwriters to process applications faster while maintaining compliance and accuracy.

### Key Features

- 🚀 **High Scale**: Process 20,000+ documents nightly using AWS Step Functions Distributed Map
- 🔒 **Enterprise Security**: KMS encryption, VPC isolation, PHI/HIPAA compliance ready
- 🤖 **Intelligent Routing**: Automatic model selection (Sonnet for complex, Haiku for simple)
- 📊 **Full Audit Trail**: DynamoDB tracking for every document processed
- ⚡ **Resilient**: Item-level retries, dead letter queues, graceful error handling
- 💰 **Cost Optimized**: ARM64 Lambda, Intelligent-Tiering S3, batch inference

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   S3 Bucket     │────▶│   SQS Queue     │────▶│ Step Functions  │
│  (Ingestion)    │     │  (Processing)   │     │ (Distributed    │
│                 │     │                 │     │     Map)        │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                               ┌─────────────────────────┼─────────────────────────┐
                               │                         │                         │
                               ▼                         ▼                         ▼
                        ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
                        │   Lambda    │          │   Lambda    │          │   Lambda    │
                        │ (Worker 1)  │          │ (Worker 2)  │    ...   │ (Worker N)  │
                        └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
                               │                         │                         │
                               └─────────────────────────┼─────────────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ Amazon Bedrock  │
                                                │ (Claude 3.5)    │
                                                └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        │                                │                                │
                        ▼                                ▼                                ▼
                 ┌─────────────┐                 ┌─────────────┐                 ┌─────────────┐
                 │  S3 Bucket  │                 │  DynamoDB   │                 │  SQS DLQ    │
                 │ (Summaries) │                 │ (Tracking)  │                 │  (Failures) │
                 └─────────────┘                 └─────────────┘                 └─────────────┘
```

### Components

| Component | Purpose | AWS Service |
|-----------|---------|-------------|
| Ingestion Bucket | Receives medical documents (PDF/TXT) | Amazon S3 |
| Processing Queue | Decouples ingestion from processing | Amazon SQS |
| Orchestration Engine | Manages parallel processing at scale | AWS Step Functions |
| AI Summarizer | Generates risk assessments | AWS Lambda + Amazon Bedrock |
| Summary Bucket | Stores generated summaries | Amazon S3 |
| Tracking Table | Audit trail and status tracking | Amazon DynamoDB |
| Dead Letter Queue | Captures failed documents | Amazon SQS |
| Nightly Trigger | Scheduled batch execution | Amazon EventBridge |

## 🚀 Quick Start

### Prerequisites

- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Python 3.12+
- Amazon Bedrock model access enabled for Claude 3.5 Sonnet and Haiku

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/lifeproof-ai.git
cd lifeproof-ai

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy
```

### Configuration

Environment variables for the Lambda function:

| Variable | Description | Default |
|----------|-------------|---------|
| `SUMMARY_BUCKET` | Output bucket for summaries | Auto-generated |
| `FAILED_BUCKET` | Bucket for failed documents | Auto-generated |
| `TRACKING_TABLE` | DynamoDB table name | `lifeproof-ai-tracking` |
| `DEFAULT_MODEL` | Bedrock model for complex docs | `anthropic.claude-3-5-sonnet-*` |
| `FAST_MODEL` | Bedrock model for simple docs | `anthropic.claude-3-5-haiku-*` |

## 📁 Project Structure

```
lifeproof-ai/
├── app.py                      # CDK app entry point
├── infrastructure/
│   └── stack.py                # Main CDK stack definition
├── lambda/
│   └── summarizer/
│       └── index.py            # AI summarization Lambda
├── scripts/
│   ├── gen_synthetic_data.py   # Synthetic test data generator
│   └── prompt_regression_test.py # Prompt validation framework
├── tests/
│   └── unit/
│       └── test_infrastructure.py # CDK unit tests
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ -v --cov=infrastructure --cov-report=html
```

### Generate Synthetic Test Data

```bash
# Generate 100 test documents locally
python scripts/gen_synthetic_data.py --count 100 --output ./test_data

# Generate and upload to S3
python scripts/gen_synthetic_data.py --count 2000 --bucket your-ingest-bucket
```

### Prompt Regression Testing

```bash
# Create sample gold standard file
python scripts/prompt_regression_test.py --create-sample ./gold_standard.jsonl

# Run regression tests
python scripts/prompt_regression_test.py --gold-standard ./gold_standard.jsonl
```

## 🔒 Security & Compliance

### Encryption

- **At Rest**: All S3 buckets and DynamoDB tables use customer-managed KMS keys
- **In Transit**: TLS 1.2+ enforced via bucket policies

### Access Control

- Lambda functions use least-privilege IAM roles
- Bedrock access is pinned to specific model ARNs
- S3 buckets block all public access

### Audit & Compliance

- Full audit trail in DynamoDB with timestamps
- Model version tracking for each summary
- Point-in-time recovery enabled on DynamoDB

## 💰 Cost Optimization

### Estimated Monthly Cost (20,000 docs/night)

| Service | Monthly Cost |
|---------|-------------|
| Amazon Bedrock (Claude 3.5) | ~$13,500 |
| AWS Step Functions | ~$75 |
| AWS Lambda (ARM64) | ~$24 |
| Amazon S3 + SQS | ~$10 |
| Amazon DynamoDB | ~$50 |
| **Total** | **~$13,659** |

### Optimization Strategies

1. **Model Routing**: Use Haiku for simple documents (saves ~70%)
2. **Prompt Caching**: Cache the underwriting rubric (saves ~90% on repeated tokens)
3. **ARM64 Lambda**: 20% cheaper than x86
4. **Intelligent-Tiering**: Automatic S3 cost optimization

## 🔧 Operations

### Manual Trigger

```bash
# Get the State Machine ARN
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name LifeProofAiStack-Dev \
  --query 'Stacks[0].Outputs[?ExportName==`LifeProofAI-StateMachine`].OutputValue' \
  --output text)

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input '{"trigger": "manual"}'
```

### Monitor Processing

```bash
# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages

# Check DLQ for failures
aws sqs get-queue-attributes \
  --queue-url $DLQ_URL \
  --attribute-names ApproximateNumberOfMessages
```

### Query Summaries by Risk Level

```bash
# Get all HIGH risk summaries
aws dynamodb query \
  --table-name lifeproof-ai-tracking \
  --index-name RiskLevelIndex \
  --key-condition-expression "risk_level = :risk" \
  --expression-attribute-values '{":risk": {"S": "HIGH"}}'
```

## 📊 QuickSight Integration

The generated summaries can be queried via Amazon Athena for QuickSight dashboards:

```sql
CREATE EXTERNAL TABLE insurance_summaries (
  processing_id string,
  risk_level string,
  conditions array<struct<name:string, onset_date:string>>,
  medications array<string>,
  underwriter_notes string,
  processing_timestamp string
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://your-summaries-bucket/summaries/';
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/unit/ -v`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [AWS CDK](https://aws.amazon.com/cdk/)
- Powered by [Amazon Bedrock](https://aws.amazon.com/bedrock/) and Claude
- Inspired by real-world life insurance underwriting challenges

---

**Made with ❤️ by the LifeProof AI Platform Team**
