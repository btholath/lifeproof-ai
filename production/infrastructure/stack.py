"""
This script defines the "Platform" logic. Notice the use of L3 Constructs for security and the Distributed Map for scale.
"""
from aws_cdk import (
    Stack, aws_s3 as s3, aws_lambda as _lambda,
    aws_stepfunctions as sfn, aws_stepfunctions_tasks as tasks,
    aws_sqs as sqs, Duration, RemovalPolicy
)
from constructs import Construct


class LifeProofAiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Secure Storage (The Ingestion Tier)
        self.ingest_bucket = s3.Bucket(self, "IngestBucket",
                                       versioned=True,
                                       enforce_ssl=True,
                                       removal_policy=RemovalPolicy.DESTROY)

        self.summary_bucket = s3.Bucket(self, "SummaryBucket",
                                        enforce_ssl=True,
                                        removal_policy=RemovalPolicy.DESTROY)

        # 2. The Worker (The AI Logic Tier)
        summarizer_fn = _lambda.Function(self, "SummarizerLambda",
                                         runtime=_lambda.Runtime.PYTHON_3_11,
                                         handler="index.handler",
                                         code=_lambda.Code.from_asset("lambda/summarizer"),
                                         timeout=Duration.seconds(120),
                                         environment={
                                             "SUMMARY_BUCKET": self.summary_bucket.bucket_name
                                         }
                                         )

        # Grant Permissions (Least Privilege)
        self.ingest_bucket.grant_read(summarizer_fn)
        self.summary_bucket.grant_write(summarizer_fn)
        # Note: In production, add Bedrock Invoke permissions here

        # 3. Orchestration (The Distributed Map)
        # This handles the 20,000 document fan-out
        process_task = tasks.LambdaInvoke(self, "SummarizeTask",
                                          lambda_function=summarizer_fn,
                                          output_path="$.Payload"
                                          )

        map_state = sfn.CustomState(self, "BatchMapProcessor",
                                    state_json={
                                        "Type": "Map",
                                        "ItemReader": {
                                            "Resource": "arn:aws:states:::s3:getObject",
                                            "ReaderConfig": {"InputType": "CSV"}
                                        },
                                        "ItemProcessor": {
                                            "ProcessorConfig": {"Mode": "DISTRIBUTED", "ExecutionType": "STANDARD"},
                                            "StartAt": "SummarizeTask",
                                            "States": {
                                                "SummarizeTask": {
                                                    "Type": "Task",
                                                    "Resource": "arn:aws:states:::lambda:invoke",
                                                    "Parameters": {
                                                        "FunctionName": summarizer_fn.function_name,
                                                        "Payload.$": "$"
                                                    },
                                                    "Retry": [{"ErrorEquals": ["States.ALL"], "IntervalSeconds": 2,
                                                               "MaxAttempts": 3}],
                                                    "End": True
                                                }
                                            }
                                        },
                                        "End": True
                                    }
                                    )

        sfn.StateMachine(self, "UnderwritingEngine",
                         definition_body=sfn.DefinitionBody.from_chainable(map_state)
                         )
