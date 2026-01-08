"""
Automated Testing (tests/unit/test_infra.py)
This proves your "Engineering Excellence."
"""
import aws_cdk as core
import aws_cdk.assertions as assertions
from infrastructure.stack import LifeProofAiStack


def test_s3_buckets_created():
    app = core.App()
    stack = LifeProofAiStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)

    # Assert that we have an Ingest and Summary bucket
    template.resource_count_is("AWS::S3::Bucket", 2)

    # Assert Step Function has Distributed Map logic
    template.has_resource_properties("AWS::StepFunctions::StateMachine", {
        "DefinitionString": assertions.Match.string_like_regexp(".*Map.*DISTRIBUTED.*")
    })
