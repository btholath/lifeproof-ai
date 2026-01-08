"""
LifeProof AI - Proof of Concept Stack

Simplified infrastructure for testing with a few documents using Claude 3.5 Haiku.
This POC version removes complexity while maintaining core functionality.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
import json


class LifeProofAiPocStack(Stack):
    """
    Simplified POC stack for Life Insurance Underwriting AI.
    
    Features:
    - Single S3 bucket for input/output
    - Lambda with Claude 3.5 Haiku
    - Simple Step Function (no Distributed Map)
    - Basic DynamoDB tracking
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ============================================================
        # 1. STORAGE - Single bucket for POC simplicity
        # ============================================================
        
        self.bucket = s3.Bucket(
            self, "PocBucket",
            versioned=True,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ============================================================
        # 2. DATABASE - Simple tracking table
        # ============================================================
        
        self.tracking_table = dynamodb.Table(
            self, "TrackingTable",
            partition_key=dynamodb.Attribute(
                name="document_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ============================================================
        # 3. LAMBDA - Summarizer with Haiku only
        # ============================================================
        
        # Lambda execution role
        summarizer_role = iam.Role(
            self, "SummarizerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # CloudWatch Logs
        summarizer_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Bedrock - Claude 3.5 Haiku only
        summarizer_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=["arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-*"]
        ))

        # Lambda Function
        self.summarizer_fn = _lambda.Function(
            self, "SummarizerLambda",
            function_name="lifeproof-poc-summarizer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda/summarizer"),
            timeout=Duration.seconds(60),
            memory_size=512,
            role=summarizer_role,
            environment={
                "BUCKET_NAME": self.bucket.bucket_name,
                "TRACKING_TABLE": self.tracking_table.table_name,
                "MODEL_ID": "anthropic.claude-3-5-haiku-20241022-v1:0",
            },
        )

        # Grant permissions
        self.bucket.grant_read_write(self.summarizer_fn)
        self.tracking_table.grant_read_write_data(self.summarizer_fn)

        # ============================================================
        # 4. STEP FUNCTION - Simple sequential processing
        # ============================================================
        
        sfn_role = iam.Role(
            self, "StepFunctionRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )
        
        self.summarizer_fn.grant_invoke(sfn_role)
        self.bucket.grant_read(sfn_role)

        # Simple definition - process list of documents
        definition = {
            "Comment": "LifeProof AI POC - Simple Document Processing",
            "StartAt": "ProcessDocuments",
            "States": {
                "ProcessDocuments": {
                    "Type": "Map",
                    "ItemsPath": "$.documents",
                    "MaxConcurrency": 5,
                    "ItemProcessor": {
                        "StartAt": "Summarize",
                        "States": {
                            "Summarize": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::lambda:invoke",
                                "Parameters": {
                                    "FunctionName": self.summarizer_fn.function_arn,
                                    "Payload.$": "$"
                                },
                                "OutputPath": "$.Payload",
                                "Retry": [
                                    {
                                        "ErrorEquals": ["States.ALL"],
                                        "IntervalSeconds": 2,
                                        "MaxAttempts": 2
                                    }
                                ],
                                "End": True
                            }
                        }
                    },
                    "End": True
                }
            }
        }

        self.state_machine = sfn.StateMachine(
            self, "PocStateMachine",
            state_machine_name="lifeproof-poc-engine",
            definition_body=sfn.DefinitionBody.from_string(json.dumps(definition)),
            role=sfn_role,
            timeout=Duration.minutes(30),
        )

        # ============================================================
        # 5. OUTPUTS
        # ============================================================
        
        CfnOutput(self, "BucketName",
            value=self.bucket.bucket_name,
            description="S3 bucket for documents and summaries"
        )

        CfnOutput(self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Step Function ARN"
        )

        CfnOutput(self, "LambdaFunctionName",
            value=self.summarizer_fn.function_name,
            description="Lambda function name"
        )

        CfnOutput(self, "TrackingTableName",
            value=self.tracking_table.table_name,
            description="DynamoDB tracking table"
        )
