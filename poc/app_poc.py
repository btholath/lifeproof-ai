#!/usr/bin/env python3
"""
LifeProof AI - POC Deployment

Simplified proof of concept stack using Claude 3.5 Haiku.

Deploy with:
    cdk deploy --app "python app_poc.py"
"""

import aws_cdk as cdk
from aws_cdk import Tags

from infrastructure.poc_stack import LifeProofAiPocStack


app = cdk.App()

stack = LifeProofAiPocStack(
    app, 
    "LifeProofAiPoc",
    description="LifeProof AI - Proof of Concept with Claude 3.5 Haiku"
)

# Tags
Tags.of(stack).add("Project", "LifeProof-AI-POC")
Tags.of(stack).add("Environment", "poc")

app.synth()

print("""
╔══════════════════════════════════════════════════════════════╗
║              LifeProof AI - Proof of Concept                ║
╠══════════════════════════════════════════════════════════════╣
║  Model: Claude 3.5 Haiku (fast & cost-effective)            ║
║                                                              ║
║  Deploy:    cdk deploy --app "python app_poc.py"            ║
║  Test:      python scripts/run_poc.py --help                ║
╚══════════════════════════════════════════════════════════════╝
""")
