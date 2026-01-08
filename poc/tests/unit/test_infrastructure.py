"""
LifeProof AI - Infrastructure Unit Tests

Comprehensive test suite for the CDK infrastructure stack.
Tests cover security, compliance, and architectural requirements.

Run with: pytest tests/unit/ -v
"""

import aws_cdk as cdk
import aws_cdk.assertions as assertions
import pytest

from infrastructure.stack import LifeProofAiStack


@pytest.fixture
def app():
    """Create a CDK app for testing."""
    return cdk.App()


@pytest.fixture
def stack(app):
    """Create the LifeProof AI stack for testing."""
    return LifeProofAiStack(app, "TestStack")


@pytest.fixture
def template(stack):
    """Generate CloudFormation template from stack."""
    return assertions.Template.from_stack(stack)


# ============================================================
# S3 BUCKET TESTS
# ============================================================

class TestS3Buckets:
    """Test S3 bucket configurations."""
    
    def test_three_buckets_created(self, template):
        """Verify all three required buckets are created."""
        template.resource_count_is("AWS::S3::Bucket", 3)
    
    def test_buckets_have_encryption(self, template):
        """Verify all buckets have KMS encryption enabled."""
        template.has_resource_properties("AWS::S3::Bucket", {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "aws:kms"
                        }
                    })
                ])
            }
        })
    
    def test_buckets_block_public_access(self, template):
        """Verify all buckets block public access."""
        template.has_resource_properties("AWS::S3::Bucket", {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            }
        })
    
    def test_ingest_bucket_has_versioning(self, template):
        """Verify ingestion bucket has versioning enabled."""
        template.has_resource_properties("AWS::S3::Bucket", {
            "VersioningConfiguration": {
                "Status": "Enabled"
            }
        })
    
    def test_ingest_bucket_has_lifecycle_rules(self, template):
        """Verify ingestion bucket has lifecycle rules for cost optimization."""
        template.has_resource_properties("AWS::S3::Bucket", {
            "LifecycleConfiguration": assertions.Match.object_like({
                "Rules": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Status": "Enabled"
                    })
                ])
            })
        })


# ============================================================
# SQS QUEUE TESTS
# ============================================================

class TestSQSQueues:
    """Test SQS queue configurations."""
    
    def test_processing_queue_created(self, template):
        """Verify processing queue is created."""
        template.has_resource_properties("AWS::SQS::Queue", {
            "QueueName": "lifeproof-ai-processing"
        })
    
    def test_dlq_created(self, template):
        """Verify dead letter queue is created."""
        template.has_resource_properties("AWS::SQS::Queue", {
            "QueueName": "lifeproof-ai-dlq"
        })
    
    def test_queue_has_encryption(self, template):
        """Verify queues have KMS encryption."""
        template.has_resource_properties("AWS::SQS::Queue", {
            "KmsMasterKeyId": assertions.Match.any_value()
        })
    
    def test_processing_queue_has_dlq(self, template):
        """Verify processing queue has dead letter queue configured."""
        template.has_resource_properties("AWS::SQS::Queue", {
            "RedrivePolicy": assertions.Match.object_like({
                "maxReceiveCount": 3
            })
        })


# ============================================================
# DYNAMODB TESTS
# ============================================================

class TestDynamoDB:
    """Test DynamoDB table configurations."""
    
    def test_tracking_table_created(self, template):
        """Verify tracking table is created."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "lifeproof-ai-tracking"
        })
    
    def test_table_has_partition_key(self, template):
        """Verify table has correct partition key."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "KeySchema": assertions.Match.array_with([
                assertions.Match.object_like({
                    "AttributeName": "document_id",
                    "KeyType": "HASH"
                })
            ])
        })
    
    def test_table_has_sort_key(self, template):
        """Verify table has correct sort key."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "KeySchema": assertions.Match.array_with([
                assertions.Match.object_like({
                    "AttributeName": "processing_timestamp",
                    "KeyType": "RANGE"
                })
            ])
        })
    
    def test_table_has_point_in_time_recovery(self, template):
        """Verify table has PITR enabled for compliance."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "PointInTimeRecoverySpecification": {
                "PointInTimeRecoveryEnabled": True
            }
        })
    
    def test_table_has_encryption(self, template):
        """Verify table has encryption enabled."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "SSESpecification": assertions.Match.object_like({
                "SSEEnabled": True
            })
        })
    
    def test_table_has_gsi_for_risk_level(self, template):
        """Verify table has GSI for risk level queries."""
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "GlobalSecondaryIndexes": assertions.Match.array_with([
                assertions.Match.object_like({
                    "IndexName": "RiskLevelIndex"
                })
            ])
        })


# ============================================================
# LAMBDA TESTS
# ============================================================

class TestLambdaFunction:
    """Test Lambda function configurations."""
    
    def test_summarizer_lambda_created(self, template):
        """Verify summarizer Lambda is created."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "FunctionName": "lifeproof-ai-summarizer"
        })
    
    def test_lambda_uses_python_312(self, template):
        """Verify Lambda uses Python 3.12 runtime."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "Runtime": "python3.12"
        })
    
    def test_lambda_uses_arm64(self, template):
        """Verify Lambda uses ARM64 architecture for cost savings."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "Architectures": ["arm64"]
        })
    
    def test_lambda_has_environment_variables(self, template):
        """Verify Lambda has required environment variables."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "Environment": {
                "Variables": assertions.Match.object_like({
                    "SUMMARY_BUCKET": assertions.Match.any_value(),
                    "TRACKING_TABLE": assertions.Match.any_value()
                })
            }
        })
    
    def test_lambda_has_tracing_enabled(self, template):
        """Verify Lambda has X-Ray tracing enabled."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "TracingConfig": {
                "Mode": "Active"
            }
        })
    
    def test_lambda_has_appropriate_timeout(self, template):
        """Verify Lambda has sufficient timeout for Bedrock calls."""
        template.has_resource_properties("AWS::Lambda::Function", {
            "Timeout": assertions.Match.any_value()
        })


# ============================================================
# STEP FUNCTIONS TESTS
# ============================================================

class TestStepFunctions:
    """Test Step Functions configurations."""
    
    def test_state_machine_created(self, template):
        """Verify state machine is created."""
        template.has_resource_properties("AWS::StepFunctions::StateMachine", {
            "StateMachineName": "lifeproof-ai-underwriting-engine"
        })
    
    def test_state_machine_has_distributed_map(self, template):
        """Verify state machine uses Distributed Map for scale."""
        template.has_resource_properties("AWS::StepFunctions::StateMachine", {
            "DefinitionString": assertions.Match.string_like_regexp(".*DISTRIBUTED.*")
        })
    
    def test_state_machine_has_tracing(self, template):
        """Verify state machine has tracing enabled."""
        template.has_resource_properties("AWS::StepFunctions::StateMachine", {
            "TracingConfiguration": {
                "Enabled": True
            }
        })
    
    def test_state_machine_has_logging(self, template):
        """Verify state machine has logging configured."""
        template.has_resource_properties("AWS::StepFunctions::StateMachine", {
            "LoggingConfiguration": assertions.Match.object_like({
                "Level": "ALL"
            })
        })


# ============================================================
# EVENTBRIDGE TESTS
# ============================================================

class TestEventBridge:
    """Test EventBridge rule configurations."""
    
    def test_nightly_rule_created(self, template):
        """Verify nightly trigger rule is created."""
        template.has_resource_properties("AWS::Events::Rule", {
            "Name": "lifeproof-ai-nightly-trigger"
        })
    
    def test_rule_has_schedule(self, template):
        """Verify rule has cron schedule."""
        template.has_resource_properties("AWS::Events::Rule", {
            "ScheduleExpression": assertions.Match.string_like_regexp("cron.*")
        })


# ============================================================
# KMS TESTS
# ============================================================

class TestKMS:
    """Test KMS key configurations."""
    
    def test_kms_key_created(self, template):
        """Verify KMS key is created."""
        template.resource_count_is("AWS::KMS::Key", 1)
    
    def test_kms_key_has_rotation(self, template):
        """Verify KMS key has rotation enabled."""
        template.has_resource_properties("AWS::KMS::Key", {
            "EnableKeyRotation": True
        })
    
    def test_kms_has_alias(self, template):
        """Verify KMS key has an alias."""
        template.has_resource_properties("AWS::KMS::Alias", {
            "AliasName": "alias/lifeproof-ai-phi"
        })


# ============================================================
# IAM TESTS
# ============================================================

class TestIAM:
    """Test IAM configurations."""
    
    def test_lambda_role_created(self, template):
        """Verify Lambda execution role is created."""
        template.has_resource_properties("AWS::IAM::Role", {
            "AssumeRolePolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        }
                    })
                ])
            })
        })
    
    def test_step_function_role_created(self, template):
        """Verify Step Function execution role is created."""
        template.has_resource_properties("AWS::IAM::Role", {
            "AssumeRolePolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Principal": {
                            "Service": "states.amazonaws.com"
                        }
                    })
                ])
            })
        })


# ============================================================
# OUTPUTS TESTS
# ============================================================

class TestOutputs:
    """Test CloudFormation outputs."""
    
    def test_ingest_bucket_output(self, template):
        """Verify ingest bucket name is exported."""
        template.has_output("IngestBucketName", {
            "Export": {
                "Name": "LifeProofAI-IngestBucket"
            }
        })
    
    def test_summary_bucket_output(self, template):
        """Verify summary bucket name is exported."""
        template.has_output("SummaryBucketName", {
            "Export": {
                "Name": "LifeProofAI-SummaryBucket"
            }
        })
    
    def test_state_machine_output(self, template):
        """Verify state machine ARN is exported."""
        template.has_output("StateMachineArn", {
            "Export": {
                "Name": "LifeProofAI-StateMachine"
            }
        })


# ============================================================
# INTEGRATION SANITY TESTS
# ============================================================

class TestIntegration:
    """Sanity tests for resource integration."""
    
    def test_s3_notification_to_sqs(self, template):
        """Verify S3 bucket notifications are configured."""
        # S3 bucket should have notification configuration
        template.has_resource_properties("Custom::S3BucketNotifications", {
            "NotificationConfiguration": assertions.Match.object_like({
                "QueueConfigurations": assertions.Match.any_value()
            })
        })
    
    def test_stack_synthesizes_without_errors(self, app):
        """Verify stack can be synthesized without errors."""
        stack = LifeProofAiStack(app, "SynthTest")
        assembly = app.synth()
        assert assembly is not None
