#!/usr/bin/env python3
"""
LifeProof AI - AWS CDK Application Entry Point

This application deploys a high-scale medical document summarization pipeline
for life insurance underwriting using Amazon Bedrock and AWS Step Functions.

Features:
- Enterprise-grade security with KMS encryption
- Automated compliance checking via CDK Aspects
- Multi-environment support (dev, staging, prod)

Usage:
    cdk synth                    # Generate CloudFormation template
    cdk deploy                   # Deploy to AWS
    cdk deploy -c environment=prod  # Deploy to production
"""

import aws_cdk as cdk
from aws_cdk import Tags, aws_s3 as s3, aws_dynamodb as dynamodb

from infrastructure.stack import LifeProofAiStack


# ============================================================
# GOVERNANCE ASPECTS - Enterprise Compliance Checkers
# ============================================================

class BucketEncryptionChecker(cdk.IAspect):
    """
    Ensures all S3 buckets have encryption enabled.
    Required for PHI/PII data compliance.
    """
    def visit(self, node):
        if isinstance(node, s3.CfnBucket):
            if not node.bucket_encryption:
                cdk.Annotations.of(node).add_warning(
                    f"S3 Bucket {node.node.path} does not have encryption configured!"
                )


class BucketVersioningChecker(cdk.IAspect):
    """
    Ensures all S3 buckets have versioning enabled for audit compliance.
    """
    def visit(self, node):
        if isinstance(node, s3.CfnBucket):
            versioning = node.versioning_configuration
            if not versioning or not getattr(versioning, 'status', None):
                cdk.Annotations.of(node).add_warning(
                    f"S3 Bucket {node.node.path} should have versioning enabled for compliance."
                )


class DynamoDBPITRChecker(cdk.IAspect):
    """
    Ensures DynamoDB tables have Point-in-Time Recovery enabled.
    """
    def visit(self, node):
        if isinstance(node, dynamodb.CfnTable):
            pitr = node.point_in_time_recovery_specification
            if not pitr or not getattr(pitr, 'point_in_time_recovery_enabled', False):
                cdk.Annotations.of(node).add_warning(
                    f"DynamoDB Table {node.node.path} should have Point-in-Time Recovery enabled."
                )


# ============================================================
# APPLICATION INITIALIZATION
# ============================================================

app = cdk.App()

# Get environment from context (default: dev)
environment = app.node.try_get_context("environment") or "dev"

# Environment-specific configurations
env_config = {
    "dev": {
        "account": None,
        "region": "us-east-1",
        "removal_policy": "DESTROY"
    },
    "staging": {
        "account": None,
        "region": "us-east-1",
        "removal_policy": "RETAIN"
    },
    "prod": {
        "account": None,
        "region": "us-east-1",
        "removal_policy": "RETAIN"
    }
}

config = env_config.get(environment, env_config["dev"])

# Create the main stack
stack = LifeProofAiStack(
    app, 
    f"LifeProofAiStack-{environment.capitalize()}",
    description=f"LifeProof AI - Medical Document Summarization Pipeline ({environment})"
)

# ============================================================
# APPLY ENTERPRISE TAGS
# ============================================================

Tags.of(stack).add("Project", "LifeProof-AI")
Tags.of(stack).add("Environment", environment)
Tags.of(stack).add("Owner", "Platform-Engineering")
Tags.of(stack).add("CostCenter", "AI-ML-Operations")
Tags.of(stack).add("Compliance", "PHI-HIPAA")
Tags.of(stack).add("DataClassification", "Confidential")

# ============================================================
# APPLY GOVERNANCE ASPECTS
# ============================================================

cdk.Aspects.of(app).add(BucketEncryptionChecker())
cdk.Aspects.of(app).add(BucketVersioningChecker())
cdk.Aspects.of(app).add(DynamoDBPITRChecker())

# ============================================================
# SYNTHESIZE
# ============================================================

app.synth()
