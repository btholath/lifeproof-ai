How to Deploy & Verify

Initialize: cdk deploy
Mock Data: Use our gen_synthetic_data.py to upload 100 files to the IngestBucket.
Execute: Trigger the Step Function from the AWS Console.
Audit: Open the SummaryBucket to see the generated JSON results.
Clean: Run our cleanup_poc.py to return to $0 spend.

This completes the end-to-end build. You now have a repository that demonstrates CDK mastery, AI/ML architectural depth, and Enterprise Governance.



Getting Started
Prerequisites
AWS Account with Amazon Bedrock model access enabled.
Python 3.11+
AWS CLI configured with appropriate permissions.

Quick Deploy
Clone the Repo: git clone https://github.com/your-org/lifeproof-ai.git
Set the Budget: python scripts/setup_safety_budget.py
Deploy Stack: sam deploy --guided
Load Test: python scripts/gen_synthetic_data.py --count 2000
