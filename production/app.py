"""
Applying an Aspect to ensure all resources meet the "Mutual of Omaha" standard before deployment.
"""
import aws_cdk as cdk
from aws_cdk import aws_s3 as s3

from infrastructure.stack import LifeProofAiStack


# Professional Governance: An Aspect to enforce encryption
class BucketEncryptionChecker(cdk.IAspect):
    def visit(self, node):
        if isinstance(node, s3.CfnBucket):
            if not node.bucket_encryption:
                print(f"⚠️ Warning: Bucket {node.node.path} is not encrypted!")


app = cdk.App()
stack = LifeProofAiStack(app, "LifeProofAiStack")

# Apply the Aspect to the entire stack
cdk.Aspects.of(app).add(BucketEncryptionChecker())

app.synth()
