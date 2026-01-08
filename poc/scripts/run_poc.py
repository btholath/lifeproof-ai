#!/usr/bin/env python3
"""
LifeProof AI - POC Test Runner

Simple script to test the POC deployment with sample documents.

Usage:
    # Upload sample documents and run Step Function
    python scripts/run_poc.py --stack-name LifeProofAiPoc
    
    # Test Lambda directly with a single document
    python scripts/run_poc.py --stack-name LifeProofAiPoc --direct
    
    # Upload only (don't trigger processing)
    python scripts/run_poc.py --stack-name LifeProofAiPoc --upload-only
    
    # View results
    python scripts/run_poc.py --stack-name LifeProofAiPoc --view-results
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)


class PocRunner:
    """Manages POC testing workflow."""
    
    def __init__(self, stack_name: str):
        self.stack_name = stack_name
        self.cf = boto3.client("cloudformation")
        self.s3 = boto3.client("s3")
        self.sfn = boto3.client("stepfunctions")
        self.lambda_client = boto3.client("lambda")
        self.dynamodb = boto3.resource("dynamodb")
        
        # Get stack outputs
        self._load_stack_outputs()
    
    def _load_stack_outputs(self):
        """Load CloudFormation stack outputs."""
        try:
            response = self.cf.describe_stacks(StackName=self.stack_name)
            outputs = response["Stacks"][0]["Outputs"]
            
            self.bucket_name = None
            self.state_machine_arn = None
            self.lambda_name = None
            self.table_name = None
            
            for output in outputs:
                key = output["OutputKey"]
                value = output["OutputValue"]
                
                if "BucketName" in key:
                    self.bucket_name = value
                elif "StateMachineArn" in key:
                    self.state_machine_arn = value
                elif "LambdaFunctionName" in key:
                    self.lambda_name = value
                elif "TrackingTableName" in key:
                    self.table_name = value
            
            if not self.bucket_name:
                raise ValueError("Could not find bucket name in stack outputs")
                
            print(f"✅ Connected to stack: {self.stack_name}")
            print(f"   Bucket: {self.bucket_name}")
            print(f"   State Machine: {self.state_machine_arn}")
            print()
            
        except ClientError as e:
            print(f"❌ Error loading stack: {e}")
            print(f"   Make sure '{self.stack_name}' is deployed")
            sys.exit(1)
    
    def upload_sample_documents(self) -> list:
        """Upload sample documents to S3."""
        sample_dir = Path(__file__).parent.parent / "sample_documents"
        
        if not sample_dir.exists():
            print(f"❌ Sample documents directory not found: {sample_dir}")
            return []
        
        documents = list(sample_dir.glob("*.txt"))
        
        if not documents:
            print("❌ No sample documents found")
            return []
        
        print(f"📤 Uploading {len(documents)} sample documents...")
        
        uploaded = []
        for doc in documents:
            key = f"uploads/{doc.name}"
            self.s3.upload_file(str(doc), self.bucket_name, key)
            uploaded.append({"bucket": self.bucket_name, "key": key})
            print(f"   ✅ {doc.name}")
        
        print()
        return uploaded
    
    def invoke_lambda_directly(self, document: dict) -> dict:
        """Invoke Lambda function directly for testing."""
        print(f"🔬 Invoking Lambda directly for: {document['key']}")
        
        response = self.lambda_client.invoke(
            FunctionName=self.lambda_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(document)
        )
        
        result = json.loads(response["Payload"].read())
        return result
    
    def start_step_function(self, documents: list) -> str:
        """Start Step Function execution."""
        print(f"🚀 Starting Step Function with {len(documents)} documents...")
        
        response = self.sfn.start_execution(
            stateMachineArn=self.state_machine_arn,
            input=json.dumps({"documents": documents})
        )
        
        execution_arn = response["executionArn"]
        print(f"   Execution ARN: {execution_arn}")
        print()
        
        return execution_arn
    
    def wait_for_completion(self, execution_arn: str, timeout: int = 300) -> dict:
        """Wait for Step Function execution to complete."""
        print("⏳ Waiting for execution to complete...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.sfn.describe_execution(executionArn=execution_arn)
            status = response["status"]
            
            if status == "SUCCEEDED":
                print("   ✅ Execution completed successfully!")
                return json.loads(response.get("output", "{}"))
            elif status in ["FAILED", "TIMED_OUT", "ABORTED"]:
                print(f"   ❌ Execution {status}")
                if "error" in response:
                    print(f"   Error: {response['error']}")
                return {"status": status}
            
            time.sleep(5)
            print(f"   Status: {status}...")
        
        print("   ⚠️ Timeout waiting for execution")
        return {"status": "TIMEOUT"}
    
    def view_results(self):
        """View summaries and tracking data."""
        print("📊 RESULTS")
        print("=" * 60)
        
        # List summaries in S3
        print("\n📁 Generated Summaries:")
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="summaries/"
            )
            
            if "Contents" not in response:
                print("   No summaries found yet")
            else:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    if key.endswith(".json"):
                        print(f"\n   📄 {key}")
                        
                        # Get and display summary
                        summary_obj = self.s3.get_object(
                            Bucket=self.bucket_name,
                            Key=key
                        )
                        summary = json.loads(summary_obj["Body"].read())
                        
                        print(f"      Patient: {summary.get('patient_name', 'Unknown')}")
                        print(f"      Risk Level: {summary.get('risk_level', 'Unknown')}")
                        print(f"      Conditions: {', '.join(summary.get('conditions', []))}")
                        if summary.get("summary"):
                            print(f"      Summary: {summary['summary'][:100]}...")
                        
        except ClientError as e:
            print(f"   Error listing summaries: {e}")
        
        # Query DynamoDB tracking
        if self.table_name:
            print("\n\n📊 Tracking Table Records:")
            try:
                table = self.dynamodb.Table(self.table_name)
                response = table.scan()
                
                if not response.get("Items"):
                    print("   No tracking records found")
                else:
                    for item in response["Items"]:
                        print(f"\n   Document: {item.get('document_id', 'Unknown')}")
                        print(f"   Status: {item.get('status', 'Unknown')}")
                        print(f"   Risk Level: {item.get('risk_level', 'N/A')}")
                        
            except ClientError as e:
                print(f"   Error querying table: {e}")
    
    def cleanup(self):
        """Clean up uploaded files."""
        print("\n🧹 Cleaning up...")
        
        # Delete uploads
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="uploads/"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    self.s3.delete_object(Bucket=self.bucket_name, Key=obj["Key"])
                print("   Deleted uploads")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Delete summaries
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="summaries/"
            )
            if "Contents" in response:
                for obj in response["Contents"]:
                    self.s3.delete_object(Bucket=self.bucket_name, Key=obj["Key"])
                print("   Deleted summaries")
        except Exception as e:
            print(f"   Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="LifeProof AI POC Test Runner")
    parser.add_argument(
        "--stack-name", type=str, default="LifeProofAiPoc",
        help="CloudFormation stack name"
    )
    parser.add_argument(
        "--upload-only", action="store_true",
        help="Only upload documents, don't process"
    )
    parser.add_argument(
        "--direct", action="store_true",
        help="Test Lambda directly instead of Step Function"
    )
    parser.add_argument(
        "--view-results", action="store_true",
        help="View existing results"
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Clean up test files"
    )
    
    args = parser.parse_args()
    
    print()
    print("🏥 LifeProof AI - POC Test Runner")
    print("=" * 60)
    print()
    
    runner = PocRunner(args.stack_name)
    
    if args.cleanup:
        runner.cleanup()
        return
    
    if args.view_results:
        runner.view_results()
        return
    
    # Upload sample documents
    documents = runner.upload_sample_documents()
    
    if not documents:
        print("No documents to process")
        return
    
    if args.upload_only:
        print("✅ Documents uploaded. Use --view-results to check after processing.")
        return
    
    if args.direct:
        # Test Lambda directly
        print("Testing Lambda directly with each document...\n")
        for doc in documents:
            result = runner.invoke_lambda_directly(doc)
            print(f"   Result: {json.dumps(result, indent=2)}\n")
    else:
        # Run Step Function
        execution_arn = runner.start_step_function(documents)
        result = runner.wait_for_completion(execution_arn)
        print(f"\nExecution Result: {json.dumps(result, indent=2)}")
    
    # Show results
    print("\n")
    runner.view_results()


if __name__ == "__main__":
    main()
