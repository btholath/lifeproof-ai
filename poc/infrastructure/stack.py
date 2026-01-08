"""
LifeProof AI - Life Insurance Policy Underwriting Review Infrastructure

This stack implements a high-scale asynchronous summarization pipeline using:
- S3 for document storage (ingestion, summaries, DLQ)
- SQS for decoupled message processing with DLQ
- Lambda for AI-powered document summarization
- Step Functions with Distributed Map for parallel processing (up to 10,000 concurrent)
- EventBridge for scheduled nightly orchestration
- DynamoDB for tracking and audit trail
- Amazon Bedrock for GenAI summarization (Claude 3.5 Sonnet/Haiku)

Architecture: Decoupled Batch Orchestration Pattern
SLA Target: All summaries ready by 8:00 AM for 20,000+ nightly documents
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
    aws_kms as kms,
)
from constructs import Construct
import json


class LifeProofAiStack(Stack):
    """
    Main infrastructure stack for the Life Insurance Underwriting AI Pipeline.
    
    Implements the "Decoupled Batch Orchestration" pattern for processing
    Attending Physician Statements (APS) and medical examination reports.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ============================================================
        # 1. ENCRYPTION & SECURITY LAYER
        # ============================================================
        
        # Customer Managed Key for PHI data encryption
        self.encryption_key = kms.Key(
            self, "PHIEncryptionKey",
            description="KMS key for encrypting PHI data in LifeProof AI",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,
            alias="alias/lifeproof-ai-phi"
        )

        # ============================================================
        # 2. STORAGE LAYER (S3 Buckets)
        # ============================================================
        
        # Ingestion Bucket - where medical PDFs land
        self.ingest_bucket = s3.Bucket(
            self, "IngestBucket",
            versioned=True,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ArchiveOldDocuments",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )

        # Summary Output Bucket - "Ready-for-Review" summaries
        self.summary_bucket = s3.Bucket(
            self, "SummaryBucket",
            versioned=True,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Failed Documents Bucket - for manual review
        self.failed_bucket = s3.Bucket(
            self, "FailedDocumentsBucket",
            versioned=True,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ============================================================
        # 3. MESSAGE QUEUE LAYER (SQS with DLQ)
        # ============================================================
        
        # Dead Letter Queue for failed messages
        self.dlq = sqs.Queue(
            self, "DeadLetterQueue",
            queue_name="lifeproof-ai-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.encryption_key,
        )

        # Main Processing Queue
        self.processing_queue = sqs.Queue(
            self, "ProcessingQueue",
            queue_name="lifeproof-ai-processing",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(7),
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=self.encryption_key,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.dlq
            )
        )

        # S3 Event Notification to SQS
        self.ingest_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(self.processing_queue),
            s3.NotificationKeyFilter(prefix="uploads/", suffix=".txt")
        )
        self.ingest_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(self.processing_queue),
            s3.NotificationKeyFilter(prefix="uploads/", suffix=".pdf")
        )

        # ============================================================
        # 4. DATABASE LAYER (DynamoDB for Audit Trail)
        # ============================================================
        
        # Tracking table for all processed documents
        self.tracking_table = dynamodb.Table(
            self, "TrackingTable",
            table_name="lifeproof-ai-tracking",
            partition_key=dynamodb.Attribute(
                name="document_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="processing_timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # GSI for querying by risk level
        self.tracking_table.add_global_secondary_index(
            index_name="RiskLevelIndex",
            partition_key=dynamodb.Attribute(
                name="risk_level",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="processing_timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # GSI for querying by processing status
        self.tracking_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="processing_timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # ============================================================
        # 5. COMPUTE LAYER (Lambda Functions)
        # ============================================================
        
        # Lambda execution role with least privilege
        summarizer_role = iam.Role(
            self, "SummarizerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="IAM role for LifeProof AI Summarizer Lambda"
        )

        # CloudWatch Logs permissions
        summarizer_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["arn:aws:logs:*:*:log-group:/aws/lambda/lifeproof-*"]
        ))

        # Bedrock permissions - pinned to specific models for security
        summarizer_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=[
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-*",
                "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-*"
            ]
        ))

        # KMS permissions for decryption
        self.encryption_key.grant_encrypt_decrypt(summarizer_role)

        # Summarizer Lambda Function
        self.summarizer_fn = _lambda.Function(
            self, "SummarizerLambda",
            function_name="lifeproof-ai-summarizer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/summarizer"),
            timeout=Duration.seconds(180),
            memory_size=1024,
            architecture=_lambda.Architecture.ARM_64,
            role=summarizer_role,
            environment={
                "SUMMARY_BUCKET": self.summary_bucket.bucket_name,
                "FAILED_BUCKET": self.failed_bucket.bucket_name,
                "TRACKING_TABLE": self.tracking_table.table_name,
                "DEFAULT_MODEL": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "FAST_MODEL": "anthropic.claude-3-5-haiku-20241022-v1:0",
                "LOG_LEVEL": "INFO"
            },
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
        )

        # Grant permissions
        self.ingest_bucket.grant_read(self.summarizer_fn)
        self.summary_bucket.grant_write(self.summarizer_fn)
        self.failed_bucket.grant_write(self.summarizer_fn)
        self.tracking_table.grant_read_write_data(self.summarizer_fn)

        # ============================================================
        # 6. ORCHESTRATION LAYER (Step Functions)
        # ============================================================
        
        # Step Function execution role
        sfn_role = iam.Role(
            self, "StepFunctionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            description="IAM role for LifeProof AI Step Function"
        )

        # Grant Lambda invoke permissions
        self.summarizer_fn.grant_invoke(sfn_role)

        # Grant S3 permissions for Distributed Map
        self.ingest_bucket.grant_read(sfn_role)
        
        # Grant SQS permissions
        self.processing_queue.grant_consume_messages(sfn_role)
        self.dlq.grant_send_messages(sfn_role)

        # CloudWatch Logs permissions for Step Functions
        sfn_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "logs:CreateLogDelivery",
                "logs:GetLogDelivery",
                "logs:UpdateLogDelivery",
                "logs:DeleteLogDelivery",
                "logs:ListLogDeliveries",
                "logs:PutResourcePolicy",
                "logs:DescribeResourcePolicies",
                "logs:DescribeLogGroups"
            ],
            resources=["*"]
        ))

        # Step Function definition using Distributed Map
        definition = {
            "Comment": "LifeProof AI - High-Scale Medical Document Summarization Pipeline",
            "StartAt": "ListDocumentsForProcessing",
            "States": {
                "ListDocumentsForProcessing": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::aws-sdk:s3:listObjectsV2",
                    "Parameters": {
                        "Bucket": self.ingest_bucket.bucket_name,
                        "Prefix": "uploads/"
                    },
                    "ResultPath": "$.s3Objects",
                    "Next": "CheckForDocuments"
                },
                "CheckForDocuments": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.s3Objects.Contents",
                            "IsPresent": True,
                            "Next": "ProcessDocumentsBatch"
                        }
                    ],
                    "Default": "NoDocumentsFound"
                },
                "NoDocumentsFound": {
                    "Type": "Pass",
                    "Result": {
                        "status": "NO_DOCUMENTS",
                        "message": "No documents found for processing"
                    },
                    "End": True
                },
                "ProcessDocumentsBatch": {
                    "Type": "Map",
                    "ItemsPath": "$.s3Objects.Contents",
                    "ItemSelector": {
                        "Bucket": self.ingest_bucket.bucket_name,
                        "Key.$": "$$.Map.Item.Value.Key"
                    },
                    "MaxConcurrency": 50,
                    "ItemProcessor": {
                        "ProcessorConfig": {
                            "Mode": "DISTRIBUTED",
                            "ExecutionType": "STANDARD"
                        },
                        "StartAt": "SummarizeDocument",
                        "States": {
                            "SummarizeDocument": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::lambda:invoke",
                                "Parameters": {
                                    "FunctionName": self.summarizer_fn.function_arn,
                                    "Payload.$": "$"
                                },
                                "Retry": [
                                    {
                                        "ErrorEquals": [
                                            "ThrottlingException",
                                            "TooManyRequestsException",
                                            "States.Timeout"
                                        ],
                                        "IntervalSeconds": 2,
                                        "MaxAttempts": 5,
                                        "BackoffRate": 2.0
                                    },
                                    {
                                        "ErrorEquals": ["States.ALL"],
                                        "IntervalSeconds": 5,
                                        "MaxAttempts": 2,
                                        "BackoffRate": 1.5
                                    }
                                ],
                                "Catch": [
                                    {
                                        "ErrorEquals": ["States.ALL"],
                                        "ResultPath": "$.error",
                                        "Next": "HandleFailedDocument"
                                    }
                                ],
                                "ResultPath": "$.result",
                                "End": True
                            },
                            "HandleFailedDocument": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::sqs:sendMessage",
                                "Parameters": {
                                    "QueueUrl": self.dlq.queue_url,
                                    "MessageBody.$": "States.JsonToString($)"
                                },
                                "End": True
                            }
                        }
                    },
                    "End": True
                }
            }
        }

        # Log group for Step Functions
        sfn_log_group = logs.LogGroup(
            self, "StepFunctionLogs",
            log_group_name="/aws/stepfunctions/lifeproof-ai",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create the State Machine
        self.state_machine = sfn.StateMachine(
            self, "UnderwritingEngine",
            state_machine_name="lifeproof-ai-underwriting-engine",
            definition_body=sfn.DefinitionBody.from_string(json.dumps(definition)),
            role=sfn_role,
            timeout=Duration.hours(6),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=sfn_log_group,
                level=sfn.LogLevel.ALL
            )
        )

        # Grant S3 ListBucket permission to Step Function role
        sfn_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:ListBucket", "s3:GetObject"],
            resources=[
                self.ingest_bucket.bucket_arn,
                f"{self.ingest_bucket.bucket_arn}/*"
            ]
        ))

        # ============================================================
        # 7. SCHEDULING LAYER (EventBridge)
        # ============================================================
        
        # Nightly trigger at 10:00 PM for overnight processing
        self.nightly_rule = events.Rule(
            self, "NightlyProcessingRule",
            rule_name="lifeproof-ai-nightly-trigger",
            description="Triggers the underwriting engine at 10:00 PM nightly",
            schedule=events.Schedule.cron(
                minute="0",
                hour="22",
                month="*",
                week_day="*",
                year="*"
            ),
            enabled=True
        )

        self.nightly_rule.add_target(
            targets.SfnStateMachine(
                self.state_machine,
                input=events.RuleTargetInput.from_object({
                    "trigger": "scheduled",
                    "timestamp": events.EventField.time
                })
            )
        )

        # ============================================================
        # 8. OUTPUTS
        # ============================================================
        
        CfnOutput(self, "IngestBucketName",
            value=self.ingest_bucket.bucket_name,
            description="S3 bucket for uploading medical documents",
            export_name="LifeProofAI-IngestBucket"
        )

        CfnOutput(self, "SummaryBucketName",
            value=self.summary_bucket.bucket_name,
            description="S3 bucket containing AI-generated summaries",
            export_name="LifeProofAI-SummaryBucket"
        )

        CfnOutput(self, "ProcessingQueueUrl",
            value=self.processing_queue.queue_url,
            description="SQS queue URL for document processing",
            export_name="LifeProofAI-ProcessingQueue"
        )

        CfnOutput(self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Step Function ARN for manual triggering",
            export_name="LifeProofAI-StateMachine"
        )

        CfnOutput(self, "TrackingTableName",
            value=self.tracking_table.table_name,
            description="DynamoDB table for audit trail",
            export_name="LifeProofAI-TrackingTable"
        )

        CfnOutput(self, "DLQUrl",
            value=self.dlq.queue_url,
            description="Dead Letter Queue for failed documents",
            export_name="LifeProofAI-DLQ"
        )
