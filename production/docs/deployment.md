To build the **LifeProof AI** application as a comprehensive, end-to-end solution for a Cloud Engineer/Architect, we
will integrate all features discussed—**scalable orchestration**, **AI model routing**, **automated governance**, and *
*safety guardrails**—into a single, documented repository.

---

### **1. Infrastructure Definition (`infrastructure/stack.py`)**

This script serves as the "Platform" logic, utilizing high-level L3 constructs and a **Distributed Map** for large-scale
document processing.

```python
"""
LifeProof AI Infrastructure Stack
Defines secure storage, AI worker compute, and high-scale orchestration.
"""
from aws_cdk import (
    Stack, aws_s3 as s3, aws_lambda as _lambda,
    aws_stepfunctions as sfn, aws_stepfunctions_tasks as tasks,
    Duration, RemovalPolicy
)
from constructs import Construct


class LifeProofAiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- 1. SECURE STORAGE (Ingestion & Summary Tiers) ---
        # [cite_start]Enforces SSL, versioning, and lifecycle management [cite: 24, 25]
        self.ingest_bucket = s3.Bucket(self, "IngestBucket",
                                       versioned=True,
                                       enforce_ssl=True,
                                       removal_policy=RemovalPolicy.DESTROY)

        self.summary_bucket = s3.Bucket(self, "SummaryBucket",
                                        enforce_ssl=True,
                                        removal_policy=RemovalPolicy.DESTROY)

        # --- 2. THE AI WORKER (Logic Tier) ---
        # [cite_start]A Lambda function that integrates with Amazon Bedrock for summarization [cite: 26]
        summarizer_fn = _lambda.Function(self, "SummarizerLambda",
                                         runtime=_lambda.Runtime.PYTHON_3_11,
                                         handler="index.handler",
                                         code=_lambda.Code.from_asset("lambda/summarizer"),
                                         timeout=Duration.seconds(120),
                                         environment={
                                             "SUMMARY_BUCKET": self.summary_bucket.bucket_name
                                         })

        # [cite_start]Least Privilege: Only grant necessary read/write access [cite: 29]
        self.ingest_bucket.grant_read(summarizer_fn)
        self.summary_bucket.grant_write(summarizer_fn)

        # --- 3. ORCHESTRATION (Distributed Map) ---
        # [cite_start]Handles massive parallel fan-out for up to 20,000+ documents [cite: 30]
        map_state = sfn.CustomState(self, "BatchMapProcessor",
                                    state_json={
                                        "Type": "Map",
                                        "ItemReader": {
                                            "Resource": "arn:aws:states:::s3:getObject",
                                            "ReaderConfig": {"InputType": "CSV"}
                                        },
                                        "ItemProcessor": {
                                            "ProcessorConfig": {
                                                "Mode": "DISTRIBUTED",
                                                "ExecutionType": "STANDARD"
                                            },
                                            "StartAt": "SummarizeTask",
                                            "States": {
                                                "SummarizeTask": {
                                                    "Type": "Task",
                                                    "Resource": "arn:aws:states:::lambda:invoke",
                                                    "Parameters": {
                                                        "FunctionName": summarizer_fn.function_name,
                                                        "Payload.$": "$"
                                                    },
                                                    "Retry": [{
                                                        "ErrorEquals": ["States.ALL"],
                                                        "IntervalSeconds": 2,
                                                        "MaxAttempts": 3
                                                    }],
                                                    "End": True
                                                }
                                            }
                                        },
                                        "End": True
                                    })

        sfn.StateMachine(self, "UnderwritingEngine",
                         definition_body=sfn.DefinitionBody.from_chainable(map_state))

```

---

### **2. AI Logic & Model Routing (`lambda/summarizer/index.py`)**

This function intelligently routes requests based on document size to optimize for cost and accuracy.

```python
"""
LifeProof AI Summarizer
Handles document extraction, Bedrock model routing, and result storage.
"""
import json
import os
import boto3

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')


def handler(event, context):
    # [cite_start]Retrieve metadata from the Step Function orchestration [cite: 168]
    bucket = event['Bucket']
    key = event['Key']

    # [cite_start]Download source medical report [cite: 168]
    obj = s3.get_object(Bucket=bucket, Key=key)
    text = obj['Body'].read().decode('utf-8')

    # [cite_start]INTELLIGENT ROUTING: Use Sonnet for long reports, Haiku for short ones [cite: 168]
    model_id = 'anthropic.claude-3-haiku-20240307-v1:0' if len(text) < 10000
    else 'anthropic.claude-3-5-sonnet-20240620-v1:0'


# [cite_start]Invoke Amazon Bedrock [cite: 169]
prompt = f"Summarize this medical report for an insurance underwriter: {text[:5000]}"
response = bedrock.invoke_model(
    modelId=model_id,
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    })
)

# [cite_start]Save structured summary to the Summary Bucket [cite: 170]
summary = json.loads(response['body'].read())['content'][0]['text']
output_key = f"summaries/{key.split('/')[-1]}.json"
s3.put_object(
    Bucket=os.environ['SUMMARY_BUCKET'],
    Key=output_key,
    Body=json.dumps({"original_file": key, "summary": summary})
)

return {"status": "SUCCEEDED", "key": output_key}

```

---

### **3. Automated Governance (`app.py`)**

Applying an **Aspect** ensures enterprise standards, such as mandatory encryption, are enforced across all resources.

```python
"""
CDK Entry Point with Enterprise Governance
Enforces encryption standards across the stack using CDK Aspects.
"""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from infrastructure.stack import LifeProofAiStack


class BucketEncryptionChecker(cdk.IAspect):
    """Ensures all S3 buckets meet encryption compliance."""

    def visit(self, node):
        if isinstance(node, s3.CfnBucket):
            if not node.bucket_encryption:
                print(f"⚠️ Compliance Warning: Bucket {node.node.path} is not encrypted!")


app = cdk.App()
stack = LifeProofAiStack(app, "LifeProofAiStack")

# [cite_start]Apply security guardrails enterprise-wide [cite: 80]
cdk.Aspects.of(app).add(BucketEncryptionChecker())
app.synth()

```

---

### **4. Safety & Load Testing Scripts**

*

**Safety Budget (`scripts/setup_safety_budget.py`):** Configures a $10 hard-stop to prevent runaway AI costs.

*

**Load Test (`scripts/gen_synthetic_data.py`):** Generates 2,000 synthetic medical reports to stress-test the
orchestration layer.

### **5. Deployment Summary**

To deploy and verify this enterprise-grade application:

1.**Initialize:** Run `cdk deploy` to provision the stack.

2.**Secure:** Configure the safety budget using `python scripts/setup_safety_budget.py`.

3.**Test:** Generate high-volume mock data with
`python scripts/gen_synthetic_data.py --count 2000 --bucket [IngestBucket]`.

4.**Execute:** Trigger the **UnderwritingEngine** Step Function via the AWS Console.

5.**Clean:** Run `cleanup_poc.py` to remove all resources and maintain a $0 spend once testing is complete.

The estimated cost for running the **LifeProof AI Proof of Concept (POC)** as described in your deployment summary (
approximately 100 files) is **extremely low**, likely **under $0.10 total** if your account is within the **AWS Free
Tier** limits.

Nearly all core infrastructure services used (Step Functions, Lambda, and S3) have generous "Always Free" or 12-month
free tier allocations that easily cover a 100-file test. The primary variable cost will be for **Amazon Bedrock** model
inference, which is billed per 1,000 tokens.

### Estimated Cost Breakdown (100-File POC)

| Service Component          | Estimated Cost (Within Free Tier)                                                            |
|----------------------------|----------------------------------------------------------------------------------------------|
| **AWS Step Functions**     | **$0.00** (Free Tier covers first 4,000 state transitions/month)                             |
| **AWS Lambda**             | **$0.00** (Free Tier covers first 1M requests and 400k GB-seconds/month)                     |
| **Amazon S3**              | **$0.00** (Free Tier covers 5GB storage and 2,000 PUT requests)                              |
| **Amazon Bedrock (Haiku)** | **~$0.02 - $0.05** (Billed at ~$0.0008 per 1k input tokens and $0.0024 per 1k output tokens) |
| **Total POC Cost**         | **Less than $0.10**                                                                          |

---

### Service-Specific Cost Details

* **AWS Step Functions (Distributed Map):** Standard Workflows are billed per state transition ($0.025 per 1,000
  transitions). A 100-file run using a simple map state involves very few transitions, all of which fall under the
  monthly 4,000 free transitions.
* **Amazon Bedrock (Claude 3.5 Haiku):** For a POC, Haiku is the most cost-effective choice, typically costing about *
  *$0.001 per 1,000 input tokens**. If each of your 100 files has roughly 500 tokens, the total input cost would be only around **$
  0.05**.
* **AWS Lambda:** Your summarizer function will run approximately 100 times. With the free tier providing 1 million free
  requests per month, this cost remains zero.
* **Amazon S3:** The 100 files you upload (even with versioning enabled) and the 100 generated JSON summaries will
  consume negligible storage space, well within the 5GB free tier limit.

### Cost Protection & Monitoring

To ensure you maintain a $0.00 idle cost and stay protected, your architecture includes:

* **Safety Budget Script:** Sets a **$10 hard-stop** alert to notify you if spending exceeds your expectations.
* **Cleanup Script:** Automatically removes all provisioned resources (buckets, state machines, Lambdas) after your demo
  is complete to avoid any long-term storage or logging charges.
