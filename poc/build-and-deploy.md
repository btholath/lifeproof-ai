```
# Deactivate the broken venv
deactivate

# Go to the correct directory (or stay in poc)
cd ~/aws_apps/lifeproof-ai/poc

# Create a new virtual environment here
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install aws-cdk-lib constructs boto3 faker

# Verify
pip list | grep aws-cdk
```

```
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ aws bedrock list-foundation-models --query "modelSummaries[?contains(modelId, 'haiku')].[modelId,modelName]" --output table
---------------------------------------------------------------------
|                       ListFoundationModels                        |
+----------------------------------------------+--------------------+
|  anthropic.claude-haiku-4-5-20251001-v1:0    |  Claude Haiku 4.5  |
|  anthropic.claude-3-haiku-20240307-v1:0:48k  |  Claude 3 Haiku    |
|  anthropic.claude-3-haiku-20240307-v1:0:200k |  Claude 3 Haiku    |
|  anthropic.claude-3-haiku-20240307-v1:0      |  Claude 3 Haiku    |
|  anthropic.claude-3-5-haiku-20241022-v1:0    |  Claude 3.5 Haiku  |
+----------------------------------------------+--------------------+
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ 
```

# Install required packages

pip install aws-cdk-lib constructs boto3

# Verify installation

pip list | grep -E "aws-cdk|constructs|boto3"

# Step 1: Bootstrap CDK (if not done before)

cdk bootstrap --app "python app_poc.py"

## What `cdk bootstrap` Did

The bootstrap command created foundational AWS resources that CDK needs to deploy your applications. This is a *
*one-time setup** per AWS account/region.

### Resources Created

| Resource           | Name                                          | Purpose                                                                   |
|--------------------|-----------------------------------------------|---------------------------------------------------------------------------|
| **S3 Bucket**      | `cdk-hnb659fds-assets-637423309379-us-east-1` | Stores Lambda code, CloudFormation templates, and other deployment assets |
| **IAM Roles**      | `cdk-hnb659fds-cfn-exec-role-*`               | Allows CloudFormation to create resources                                 |
|                    | `cdk-hnb659fds-deploy-role-*`                 | Allows CDK to deploy stacks                                               |
|                    | `cdk-hnb659fds-lookup-role-*`                 | Allows CDK to look up existing resources                                  |
|                    | `cdk-hnb659fds-file-publishing-role-*`        | Allows uploading assets to S3                                             |
|                    | `cdk-hnb659fds-image-publishing-role-*`       | Allows pushing Docker images to ECR                                       |
| **SSM Parameter**  | `/cdk-bootstrap/hnb659fds/version`            | Tracks bootstrap version                                                  |
| **ECR Repository** | `cdk-hnb659fds-container-assets-*`            | Stores Docker images (if needed)                                          |

---

## Where to See This in AWS Console

### 1. CloudFormation

```
Console → CloudFormation → Stacks → "CDKToolkit"
```

You'll see the bootstrap stack with status `CREATE_COMPLETE`

![CloudFormation location]

### 2. S3 Bucket

```
Console → S3 → Search for "cdk-hnb659fds-assets"
```

This bucket will store your Lambda code when you deploy

### 3. IAM Roles

```
Console → IAM → Roles → Search for "cdk-hnb659fds"
```

You'll see 4-5 roles created for CDK operations

### 4. SSM Parameter

```
Console → Systems Manager → Parameter Store → Search "/cdk-bootstrap"
```

---

## Next Step: Deploy Your Application (POC stack)

Now run the actual deployment:

```bash
cdk deploy --app "python app_poc.py"
```

This will create your **actual application resources**:

- S3 bucket for medical documents
- Lambda function with Claude 3.5 Haiku
- Step Functions state machine
- DynamoDB tracking table

Type `y` when prompted to confirm the IAM changes.

```
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ cdk bootstrap --app "python app_poc.py"

╔══════════════════════════════════════════════════════════════╗
║              LifeProof AI - Proof of Concept                ║
╠══════════════════════════════════════════════════════════════╣
║  Model: Claude 3.5 Haiku (fast & cost-effective)            ║
║                                                              ║
║  Deploy:    cdk deploy --app "python app_poc.py"            ║
║  Test:      python scripts/run_poc.py --help                ║
╚══════════════════════════════════════════════════════════════╝

 ⏳  Bootstrapping environment aws://637423309379/us-east-1...
Trusted accounts for deployment: (none)
Trusted accounts for lookup: (none)
Using default execution policy of 'arn:aws:iam::aws:policy/AdministratorAccess'. Pass '--cloudformation-execution-policies' to customize.
CDKToolkit: creating CloudFormation changeset...
 ✅  Environment aws://637423309379/us-east-1 bootstrapped.
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ cdk deploy --app "python app_poc.py"

╔══════════════════════════════════════════════════════════════╗
║              LifeProof AI - Proof of Concept                ║
╠══════════════════════════════════════════════════════════════╣
║  Model: Claude 3.5 Haiku (fast & cost-effective)            ║
║                                                              ║
║  Deploy:    cdk deploy --app "python app_poc.py"            ║
║  Test:      python scripts/run_poc.py --help                ║
╚══════════════════════════════════════════════════════════════╝

[Warning at /LifeProofAiPoc/SummarizerRole] Failed to add method metadata for node [SummarizerRole], method name addManagedPolicy. Reason: ValidationError: The result of fromAwsManagedPolicyName can not be used in this API [ack: @aws-cdk/core:addMethodMetadataFailed]

✨  Synthesis time: 26.68s

LifeProofAiPoc: start: Building LifeProofAiPoc/Custom::S3AutoDeleteObjectsCustomResourceProvider Code
LifeProofAiPoc: success: Built LifeProofAiPoc/Custom::S3AutoDeleteObjectsCustomResourceProvider Code
LifeProofAiPoc: start: Building SummarizerLambda/Code
LifeProofAiPoc: success: Built SummarizerLambda/Code
LifeProofAiPoc: start: Building LifeProofAiPoc Template
LifeProofAiPoc: success: Built LifeProofAiPoc Template
LifeProofAiPoc: start: Publishing LifeProofAiPoc/Custom::S3AutoDeleteObjectsCustomResourceProvider Code (current_account-current_region-e31788a2)
LifeProofAiPoc: start: Publishing SummarizerLambda/Code (current_account-current_region-60f7052f)
LifeProofAiPoc: start: Publishing LifeProofAiPoc Template (current_account-current_region-5aa87efb)
LifeProofAiPoc: success: Published LifeProofAiPoc/Custom::S3AutoDeleteObjectsCustomResourceProvider Code (current_account-current_region-e31788a2)
LifeProofAiPoc: success: Published SummarizerLambda/Code (current_account-current_region-60f7052f)
LifeProofAiPoc: success: Published LifeProofAiPoc Template (current_account-current_region-5aa87efb)
Stack LifeProofAiPoc
IAM Statement Changes
┌───┬──────────────────────────────────────────────────────────────────┬────────┬─────────────────────────────┬───────────────────────────────────────────────────────────────────┬──────────────────────────────────┐
│   │ Resource                                                         │ Effect │ Action                      │ Principal                                                         │ Condition                        │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${Custom::S3AutoDeleteObjectsCustomResourceProvider/Role.Arn}    │ Allow  │ sts:AssumeRole              │ Service:lambda.amazonaws.com                                      │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${PocBucket.Arn}                                                 │ Deny   │ s3:*                        │ AWS:*                                                             │ "Bool": {                        │
│   │ ${PocBucket.Arn}/*                                               │        │                             │                                                                   │   "aws:SecureTransport": "false" │
│   │                                                                  │        │                             │                                                                   │ }                                │
│ + │ ${PocBucket.Arn}                                                 │ Allow  │ s3:DeleteObject*            │ AWS:${Custom::S3AutoDeleteObjectsCustomResourceProvider/Role.Arn} │                                  │
│   │ ${PocBucket.Arn}/*                                               │        │ s3:GetBucket*               │                                                                   │                                  │
│   │                                                                  │        │ s3:List*                    │                                                                   │                                  │
│   │                                                                  │        │ s3:PutBucketPolicy          │                                                                   │                                  │
│ + │ ${PocBucket.Arn}                                                 │ Allow  │ s3:Abort*                   │ AWS:${SummarizerRole}                                             │                                  │
│   │ ${PocBucket.Arn}/*                                               │        │ s3:DeleteObject*            │                                                                   │                                  │
│   │                                                                  │        │ s3:GetBucket*               │                                                                   │                                  │
│   │                                                                  │        │ s3:GetObject*               │                                                                   │                                  │
│   │                                                                  │        │ s3:List*                    │                                                                   │                                  │
│   │                                                                  │        │ s3:PutObject                │                                                                   │                                  │
│   │                                                                  │        │ s3:PutObjectLegalHold       │                                                                   │                                  │
│   │                                                                  │        │ s3:PutObjectRetention       │                                                                   │                                  │
│   │                                                                  │        │ s3:PutObjectTagging         │                                                                   │                                  │
│   │                                                                  │        │ s3:PutObjectVersionTagging  │                                                                   │                                  │
│ + │ ${PocBucket.Arn}                                                 │ Allow  │ s3:GetBucket*               │ AWS:${StepFunctionRole}                                           │                                  │
│   │ ${PocBucket.Arn}/*                                               │        │ s3:GetObject*               │                                                                   │                                  │
│   │                                                                  │        │ s3:List*                    │                                                                   │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${StepFunctionRole.Arn}                                          │ Allow  │ sts:AssumeRole              │ Service:states.amazonaws.com                                      │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${SummarizerLambda.Arn}                                          │ Allow  │ lambda:InvokeFunction       │ AWS:${StepFunctionRole}                                           │                                  │
│   │ ${SummarizerLambda.Arn}:*                                        │        │                             │                                                                   │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${SummarizerRole.Arn}                                            │ Allow  │ sts:AssumeRole              │ Service:lambda.amazonaws.com                                      │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ ${TrackingTable.Arn}                                             │ Allow  │ dynamodb:BatchGetItem       │ AWS:${SummarizerRole}                                             │                                  │
│   │                                                                  │        │ dynamodb:BatchWriteItem     │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:ConditionCheckItem │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:DeleteItem         │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:DescribeTable      │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:GetItem            │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:GetRecords         │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:GetShardIterator   │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:PutItem            │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:Query              │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:Scan               │                                                                   │                                  │
│   │                                                                  │        │ dynamodb:UpdateItem         │                                                                   │                                  │
├───┼──────────────────────────────────────────────────────────────────┼────────┼─────────────────────────────┼───────────────────────────────────────────────────────────────────┼──────────────────────────────────┤
│ + │ arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-* │ Allow  │ bedrock:InvokeModel         │ AWS:${SummarizerRole}                                             │                                  │
└───┴──────────────────────────────────────────────────────────────────┴────────┴─────────────────────────────┴───────────────────────────────────────────────────────────────────┴──────────────────────────────────┘
IAM Policy Changes
┌───┬───────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────┐
│   │ Resource                                                  │ Managed Policy ARN                                                                           │
├───┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ + │ ${Custom::S3AutoDeleteObjectsCustomResourceProvider/Role} │ {"Fn::Sub":"arn:${AWS::Partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"} │
├───┼───────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┤
│ + │ ${SummarizerRole}                                         │ arn:${AWS::Partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole               │
└───┴───────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────┘
(NOTE: There may be security-related changes not in this list. See https://github.com/aws/aws-cdk/issues/1299)


"--require-approval" is enabled and stack includes security-sensitive updates: 'Do you wish to deploy these changes' (y/n) y
LifeProofAiPoc: deploying... [1/1]
LifeProofAiPoc: creating CloudFormation changeset...

 ✅  LifeProofAiPoc

✨  Deployment time: 82.11s

Outputs:
LifeProofAiPoc.BucketName = lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje
LifeProofAiPoc.LambdaFunctionName = lifeproof-poc-summarizer
LifeProofAiPoc.StateMachineArn = arn:aws:states:us-east-1:637423309379:stateMachine:lifeproof-poc-engine
LifeProofAiPoc.TrackingTableName = LifeProofAiPoc-TrackingTable170A6688-1Q8WSCPOD9BY3
Stack ARN:
arn:aws:cloudformation:us-east-1:637423309379:stack/LifeProofAiPoc/6e9368d0-ec18-11f0-a86f-0affe5c8e2a5

✨  Total time: 108.79s

(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ 
```

```
🎉 **Deployment Successful!** 

## What Was Created

| Resource | Name/ARN | Purpose |
|----------|----------|---------|
| **S3 Bucket** | `lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje` | Stores medical documents & summaries |
| **Lambda Function** | `lifeproof-poc-summarizer` | Runs Claude 3.5 Haiku for summarization |
| **Step Functions** | `lifeproof-poc-engine` | Orchestrates document processing |
| **DynamoDB Table** | `LifeProofAiPoc-TrackingTable170A6688-1Q8WSCPOD9BY3` | Tracks processing status |

### IAM Permissions Created:
- ✅ Lambda can invoke **Bedrock Claude 3.5 Haiku**
- ✅ Lambda can read/write to **S3 bucket**
- ✅ Lambda can write to **DynamoDB**
- ✅ Step Functions can invoke **Lambda**
- ✅ S3 enforces **HTTPS only** (secure transport)

---

## View in AWS Console

### CloudFormation
```

Console → CloudFormation → Stacks → "LifeProofAiPoc"

```

### S3 Bucket
```

Console → S3 → "lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje"

```

### Lambda Function
```

Console → Lambda → Functions → "lifeproof-poc-summarizer"

```

### Step Functions
```

Console → Step Functions → State machines → "lifeproof-poc-engine"

```

---

## Now Test It!

```bash
python scripts/run_poc.py --stack-name LifeProofAiPoc
```

This will:

1. Upload 3 sample medical documents (LOW, MEDIUM, HIGH risk)
2. Run the Step Function
3. Call Claude 3.5 Haiku to analyze each document
4. Display the AI-generated risk assessments

```
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ python scripts/run_poc.py --stack-name LifeProofAiPoc

🏥 LifeProof AI - POC Test Runner
============================================================

✅ Connected to stack: LifeProofAiPoc
   Bucket: lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje
   State Machine: arn:aws:states:us-east-1:637423309379:stateMachine:lifeproof-poc-engine

📤 Uploading 3 sample documents...
   ✅ APS_MEDIUM_RISK_Robert_Martinez.txt
   ✅ APS_LOW_RISK_Sarah_Johnson.txt
   ✅ APS_HIGH_RISK_James_Wilson.txt

🚀 Starting Step Function with 3 documents...
   Execution ARN: arn:aws:states:us-east-1:637423309379:execution:lifeproof-poc-engine:39abd0b5-f1d1-41f4-92c6-1abe5f5646ba

⏳ Waiting for execution to complete...
   Status: RUNNING...
   Status: RUNNING...
   ❌ Execution FAILED
   Error: ValidationException

Execution Result: {
  "status": "FAILED"
}


📊 RESULTS
============================================================

📁 Generated Summaries:
   No summaries found yet


📊 Tracking Table Records:

   Document: uploads/APS_HIGH_RISK_James_Wilson.txt
   Status: FAILED
   Risk Level: ERROR

   Document: uploads/APS_LOW_RISK_Sarah_Johnson.txt
   Status: FAILED
   Risk Level: ERROR

   Document: uploads/APS_MEDIUM_RISK_Robert_Martinez.txt
   Status: FAILED
   Risk Level: ERROR
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ aws lambda update-function-configuration \
  --function-name lifeproof-poc-summarizer \
  --environment "Variables={BUCKET_NAME=lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje,TRACKING_TABLE=LifeProofAiPoc-TrackingTable170A6688-1Q8WSCPOD9BY3,MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0}"
{
    "FunctionName": "lifeproof-poc-summarizer",
    "FunctionArn": "arn:aws:lambda:us-east-1:637423309379:function:lifeproof-poc-summarizer",
    "Runtime": "python3.12",
    "Role": "arn:aws:iam::637423309379:role/LifeProofAiPoc-SummarizerRoleEACFAB97-LRrko1dUegwm",
    "Handler": "index.handler",
    "CodeSize": 8590,
    "Description": "",
    "Timeout": 60,
    "MemorySize": 512,
    "LastModified": "2026-01-07T22:46:05.000+0000",
    "CodeSha256": "cLK2OivTw1I8P+HadIHWeIcfRNBE13mJAaUgUGuqV/A=",
    "Version": "$LATEST",
    "Environment": {
        "Variables": {
            "MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "TRACKING_TABLE": "LifeProofAiPoc-TrackingTable170A6688-1Q8WSCPOD9BY3",
            "BUCKET_NAME": "lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje"
        }
    },
    "TracingConfig": {
        "Mode": "PassThrough"
    },
    "RevisionId": "fd792b82-2505-4a91-b94d-0df4761d10e9",
    "State": "Active",
    "LastUpdateStatus": "InProgress",
    "LastUpdateStatusReason": "The function is being created.",
    "LastUpdateStatusReasonCode": "Creating",
    "PackageType": "Zip",
    "Architectures": [
        "x86_64"
    ],
    "EphemeralStorage": {
        "Size": 512
    },
    "SnapStart": {
        "ApplyOn": "None",
        "OptimizationStatus": "Off"
    },
    "RuntimeVersionConfig": {
        "RuntimeVersionArn": "arn:aws:lambda:us-east-1::runtime:994aac32248ecf4d69d9f5e9a3a57aba3ccea19d94170a61d5ecf978927e1b0f"
    },
    "LoggingConfig": {
        "LogFormat": "Text",
        "LogGroup": "/aws/lambda/lifeproof-poc-summarizer"
    }
}
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ python scripts/run_poc.py --stack-name LifeProofAiPoc

🏥 LifeProof AI - POC Test Runner
============================================================

✅ Connected to stack: LifeProofAiPoc
   Bucket: lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje
   State Machine: arn:aws:states:us-east-1:637423309379:stateMachine:lifeproof-poc-engine

📤 Uploading 3 sample documents...
   ✅ APS_MEDIUM_RISK_Robert_Martinez.txt
   ✅ APS_LOW_RISK_Sarah_Johnson.txt
   ✅ APS_HIGH_RISK_James_Wilson.txt

🚀 Starting Step Function with 3 documents...
   Execution ARN: arn:aws:states:us-east-1:637423309379:execution:lifeproof-poc-engine:72d0e268-bb2e-4b6b-9453-7e523bb285c1

⏳ Waiting for execution to complete...
   Status: RUNNING...
   Status: RUNNING...
   ❌ Execution FAILED
   Error: AccessDeniedException

Execution Result: {
  "status": "FAILED"
}


📊 RESULTS
============================================================

📁 Generated Summaries:
   No summaries found yet


📊 Tracking Table Records:

   Document: uploads/APS_HIGH_RISK_James_Wilson.txt
   Status: FAILED
   Risk Level: ERROR

   Document: uploads/APS_LOW_RISK_Sarah_Johnson.txt
   Status: FAILED
   Risk Level: ERROR

   Document: uploads/APS_MEDIUM_RISK_Robert_Martinez.txt
   Status: FAILED
   Risk Level: ERROR
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ # Add permission for Claude 3 Haiku
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ # Add permission for Claude 3 Haiku
aws iam put-role-policy \Poc-SummarizerRoleEACFAB97-LRrko1dUegwm \
  --role-name LifeProofAiPoc-SummarizerRoleEACFAB97-LRrko1dUegwm \
  --policy-name BedrockClaude3HaikuAccess \
  --policy-document '{0-17",
    "Version": "2012-10-17",
    "Statement": [
      { "Effect": "Allow",
        "Effect": "Allow",:InvokeModel",
        "Action": "bedrock:InvokeModel",
        "Resource": [drock:*::foundation-model/anthropic.claude-3-haiku-*",
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*","
          "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-*"
        ]
      }
    ]
  }'
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ python scripts/run_poc.py --stack-name LifeProofAiPoc

🏥 LifeProof AI - POC Test Runner
============================================================

✅ Connected to stack: LifeProofAiPoc
   Bucket: lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje
   State Machine: arn:aws:states:us-east-1:637423309379:stateMachine:lifeproof-poc-engine

📤 Uploading 3 sample documents...
   ✅ APS_MEDIUM_RISK_Robert_Martinez.txt
   ✅ APS_LOW_RISK_Sarah_Johnson.txt
   ✅ APS_HIGH_RISK_James_Wilson.txt

🚀 Starting Step Function with 3 documents...
   Execution ARN: arn:aws:states:us-east-1:637423309379:execution:lifeproof-poc-engine:e55177b4-82ad-4d5e-994c-f07b7afac453

⏳ Waiting for execution to complete...
   Status: RUNNING...
   Status: RUNNING...
   ✅ Execution completed successfully!

Execution Result: [
  {
    "status": "SUCCEEDED",
    "processing_id": "9f16da78-c1dc-4140-aace-fef7aec40e60",
    "input_key": "uploads/APS_MEDIUM_RISK_Robert_Martinez.txt",
    "output_key": "summaries/APS_MEDIUM_RISK_Robert_Martinez_summary.json",
    "risk_level": "MEDIUM",
    "model_used": "anthropic.claude-3-haiku-20240307-v1:0"
  },
  {
    "status": "SUCCEEDED",
    "processing_id": "bfa43894-b92d-4242-b3f3-6d7830e223ab",
    "input_key": "uploads/APS_LOW_RISK_Sarah_Johnson.txt",
    "output_key": "summaries/APS_LOW_RISK_Sarah_Johnson_summary.json",
    "risk_level": "LOW",
    "model_used": "anthropic.claude-3-haiku-20240307-v1:0"
  },
  {
    "status": "SUCCEEDED",
    "processing_id": "078d0161-b1cb-4c43-b39e-ed0e00e5bc66",
    "input_key": "uploads/APS_HIGH_RISK_James_Wilson.txt",
    "output_key": "summaries/APS_HIGH_RISK_James_Wilson_summary.json",
    "risk_level": "HIGH",
    "model_used": "anthropic.claude-3-haiku-20240307-v1:0"
  }
]


📊 RESULTS
============================================================

📁 Generated Summaries:

   📄 summaries/APS_HIGH_RISK_James_Wilson_summary.json
      Patient: Unknown
      Risk Level: HIGH
Traceback (most recent call last):
  File "/home/bijut/aws_apps/lifeproof-ai/poc/scripts/run_poc.py", line 320, in <module>
    main()
  File "/home/bijut/aws_apps/lifeproof-ai/poc/scripts/run_poc.py", line 316, in main
    runner.view_results()
  File "/home/bijut/aws_apps/lifeproof-ai/poc/scripts/run_poc.py", line 195, in view_results
    print(f"      Conditions: {', '.join(summary.get('conditions', []))}")
                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: sequence item 0: expected str instance, dict found
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ # View HIGH risk summary
aws s3 cp s3://lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje/summaries/APS_HIGH_RISK_James_Wilson_summary.json - | jq .

# View MEDIUM risk summary
aws s3 cp s3://lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje/summaries/APS_MEDIUM_RISK_Robert_Martinez_summary.json - | jq .

# View LOW risk summary
aws s3 cp s3://lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje/summaries/APS_LOW_RISK_Sarah_Johnson_summary.json - | jq .
{
  "patient_id": "MRN-334456",
  "processing_id": "078d0161-b1cb-4c43-b39e-ed0e00e5bc66",
  "risk_level": "HIGH",
  "risk_factors": [
    "Myocardial Infarction within the last 5 years",
    "Left Ventricular Ejection Fraction (LVEF) < 45%",
    "Insulin-dependent diabetes with HbA1c > 9.0%",
    "Current tobacco use",
    "Heavy alcohol use",
    "Stage 3a Chronic Kidney Disease (GFR 30-60)"
  ],
  "conditions": [
    {
      "name": "Coronary Artery Disease s/p STEMI",
      "onset_date": "March 2023",
      "status": "active"
    },
    {
      "name": "Ischemic Cardiomyopathy with reduced LVEF",
      "onset_date": "March 2023",
      "status": "active"
    },
    {
      "name": "Type 2 Diabetes Mellitus",
      "onset_date": "Not found in report",
      "status": "active"
    },
    {
      "name": "Essential Hypertension",
      "onset_date": "Not found in report",
      "status": "active"
    },
    {
      "name": "Hyperlipidemia",
      "onset_date": "Not found in report",
      "status": "active"
    }
  ],
  "medications": [
    {
      "name": "Aspirin",
      "dosage": "81mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Clopidogrel",
      "dosage": "75mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Metoprolol succinate",
      "dosage": "100mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Lisinopril",
      "dosage": "40mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Atorvastatin",
      "dosage": "80mg daily",
      "compliance": "non-compliant"
    },
    {
      "name": "Metformin",
      "dosage": "1000mg twice daily",
      "compliance": "compliant"
    },
    {
      "name": "Glipizide",
      "dosage": "10mg twice daily",
      "compliance": "compliant"
    },
    {
      "name": "Empagliflozin",
      "dosage": "25mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Furosemide",
      "dosage": "20mg daily",
      "compliance": "compliant"
    }
  ],
  "surgeries": [
    {
      "procedure": "PCI with DES to LAD",
      "date": "March 2023",
      "outcome": "Not found in report"
    },
    {
      "procedure": "Cardiac catheterization",
      "date": "March 2023",
      "outcome": "Not found in report"
    },
    {
      "procedure": "Appendectomy",
      "date": "1995",
      "outcome": "Not found in report"
    }
  ],
  "lifestyle_flags": {
    "tobacco": "current",
    "alcohol": "heavy",
    "hazardous_activities": []
  },
  "lab_values": {
    "HbA1c": "9.2%",
    "GFR": "58 mL/min",
    "LVEF": "40%",
    "LDL": "142 mg/dL"
  },
  "underwriter_notes": "This patient presents with multiple high-risk factors, including recent myocardial infarction with reduced left ventricular ejection fraction, poorly controlled type 2 diabetes, current heavy smoking, and heavy alcohol use. The combination of these factors significantly increases the patient's mortality risk, warranting a high-risk classification.",
  "confidence_score": "HIGH",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "original_document": "uploads/APS_HIGH_RISK_James_Wilson.txt",
  "generated_at": "2026-01-07T22:48:53.617130+00:00"
}
{
  "patient_id": "MRN-778834",
  "processing_id": "9f16da78-c1dc-4140-aace-fef7aec40e60",
  "risk_level": "MEDIUM",
  "risk_factors": [
    "Managed Type 2 Diabetes (HbA1c 7.0-9.0%)",
    "Treated Hypertension requiring 2+ medications",
    "Former tobacco use (quit 2022)"
  ],
  "conditions": [
    {
      "name": "Type 2 Diabetes Mellitus",
      "onset_date": "2020",
      "status": "managed"
    },
    {
      "name": "Essential Hypertension",
      "onset_date": "2019",
      "status": "managed"
    },
    {
      "name": "Hyperlipidemia",
      "onset_date": "2020",
      "status": "managed"
    },
    {
      "name": "Obesity",
      "onset_date": "Not found in report",
      "status": "active"
    },
    {
      "name": "Former tobacco use",
      "onset_date": "Not found in report",
      "status": "resolved"
    }
  ],
  "medications": [
    {
      "name": "Metformin",
      "dosage": "1000mg twice daily",
      "compliance": "compliant"
    },
    {
      "name": "Lisinopril",
      "dosage": "20mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Amlodipine",
      "dosage": "5mg daily",
      "compliance": "compliant"
    },
    {
      "name": "Atorvastatin",
      "dosage": "20mg at bedtime",
      "compliance": "compliant"
    },
    {
      "name": "Aspirin",
      "dosage": "81mg daily",
      "compliance": "compliant"
    }
  ],
  "surgeries": [
    {
      "procedure": "Cholecystectomy",
      "date": "2018",
      "outcome": "Not found in report"
    },
    {
      "procedure": "Knee arthroscopy",
      "date": "2015",
      "outcome": "Not found in report"
    }
  ],
  "lifestyle_flags": {
    "tobacco": "former",
    "alcohol": "moderate",
    "hazardous_activities": []
  },
  "lab_values": {
    "HbA1c": "7.4%",
    "GFR": "72 mL/min",
    "LVEF": "Not found in report",
    "LDL": "98 mg/dL"
  },
  "underwriter_notes": "The applicant has a history of managed Type 2 Diabetes and Hypertension, with a former 20 pack-year smoking history. His current HbA1c of 7.4% and mildly reduced GFR of 72 mL/min indicate his conditions are being actively managed, but not fully controlled. This places him in the MEDIUM risk category for underwriting.",
  "confidence_score": "HIGH",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "original_document": "uploads/APS_MEDIUM_RISK_Robert_Martinez.txt",
  "generated_at": "2026-01-07T22:48:54.144052+00:00"
}
{
  "patient_id": "MRN-445521",
  "processing_id": "bfa43894-b92d-4242-b3f3-6d7830e223ab",
  "risk_level": "LOW",
  "risk_factors": [],
  "conditions": [
    {
      "name": "Seasonal allergies",
      "onset_date": "Not found in report",
      "status": "managed"
    },
    {
      "name": "Vitamin D insufficiency",
      "onset_date": "Not found in report",
      "status": "active"
    }
  ],
  "medications": [
    {
      "name": "Cetirizine",
      "dosage": "10mg daily PRN",
      "compliance": "compliant"
    },
    {
      "name": "Vitamin D3",
      "dosage": "2000 IU daily",
      "compliance": "compliant"
    },
    {
      "name": "Multivitamin",
      "dosage": "daily",
      "compliance": "compliant"
    }
  ],
  "surgeries": [],
  "lifestyle_flags": {
    "tobacco": "never",
    "alcohol": "moderate",
    "hazardous_activities": []
  },
  "lab_values": {
    "HbA1c": "5.2%",
    "GFR": "105 mL/min",
    "LVEF": "Not found",
    "LDL": "102 mg/dL"
  },
  "underwriter_notes": "The applicant is a healthy 40-year-old female with no significant medical conditions. She has an excellent cardiovascular risk profile with normal lab values and no history of major medical events. The applicant maintains a healthy lifestyle with regular exercise and no tobacco use. Based on the information provided, this applicant would be considered a standard risk candidate.",
  "confidence_score": "HIGH",
  "model_used": "anthropic.claude-3-haiku-20240307-v1:0",
  "original_document": "uploads/APS_LOW_RISK_Sarah_Johnson.txt",
  "generated_at": "2026-01-07T22:48:49.130290+00:00"
}
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ # List all summaries
aws s3 ls s3://lifeproofaipoc-pocbucket4d57a3c8-azzj909ykxje/summaries/
2026-01-07 14:48:54       3195 APS_HIGH_RISK_James_Wilson_summary.json
2026-01-07 14:48:50       1594 APS_LOW_RISK_Sarah_Johnson_summary.json
2026-01-07 14:48:55       2429 APS_MEDIUM_RISK_Robert_Martinez_summary.json
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ aws dynamodb scan --table-name LifeProofAiPoc-TrackingTable170A6688-1Q8WSCPOD9BY3 | jq '.Items[] | {document: .document_id.S, status: .status.S, risk: .risk_level.S}'
{
  "document": "uploads/APS_HIGH_RISK_James_Wilson.txt",
  "status": "COMPLETED",
  "risk": "HIGH"
}
{
  "document": "uploads/APS_LOW_RISK_Sarah_Johnson.txt",
  "status": "COMPLETED",
  "risk": "LOW"
}
{
  "document": "uploads/APS_MEDIUM_RISK_Robert_Martinez.txt",
  "status": "COMPLETED",
  "risk": "MEDIUM"
}
(.venv) bijut@b:~/aws_apps/lifeproof-ai/poc$ 


```