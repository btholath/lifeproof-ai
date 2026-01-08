I'll start by reviewing the uploaded files to understand what needs to be built.Now I have a complete understanding of
the project. This is a **Life Insurance Policy Underwriting Review** system that uses AWS CDK, Step Functions with
Distributed Map, Lambda, and Amazon Bedrock for AI-powered medical document summarization.

Let me build the complete, production-ready application:I've built the complete **LifeProof AI** application - a
production-ready, high-scale medical document summarization pipeline for life insurance underwriting. Here's what's
included:

## 📦 Project Components

### 1. **Infrastructure Stack** (`infrastructure/stack.py`)

- **S3 Buckets**: Ingestion, Summaries, Failed Documents (all KMS encrypted)
- **SQS Queues**: Processing queue with Dead Letter Queue for resilience
- **DynamoDB**: Audit trail table with GSIs for risk level and status queries
- **Lambda Function**: ARM64, Python 3.12, X-Ray tracing enabled
- **Step Functions**: Distributed Map for processing 20,000+ documents in parallel
- **EventBridge**: Nightly trigger at 10:00 PM
- **KMS**: Customer-managed key with rotation for PHI compliance

### 2. **Lambda Summarizer** (`lambda/summarizer/index.py`)

- Intelligent model routing (Sonnet for complex, Haiku for simple documents)
- Comprehensive underwriting rubric with risk classification (HIGH/MEDIUM/LOW)
- Chain-of-Thought prompting for clinical accuracy
- Structured JSON output with conditions, medications, labs, and risk factors
- Full error handling and audit logging

### 3. **Scripts**

- **`gen_synthetic_data.py`**: Generates realistic synthetic medical documents for testing
- **`prompt_regression_test.py`**: LLM-as-a-Judge validation framework for prompt changes

### 4. **Tests** (`tests/unit/test_infrastructure.py`)

- 30+ unit tests covering security, compliance, and architecture
- Tests for S3 encryption, DynamoDB PITR, Lambda configuration, etc.

### 5. **Governance** (`app.py`)

- CDK Aspects for automated compliance checking
- Enterprise tagging (Project, Environment, Compliance, Owner)
- Multi-environment support (dev, staging, prod)

## 🚀 Quick Start

```bash
# Extract and deploy
tar -xzf lifeproof-ai-complete.tar.gz
cd lifeproof-ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap && cdk deploy
```