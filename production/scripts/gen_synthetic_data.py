"""
File: scripts/gen_synthetic_data.py This script uses the Faker library to generate 2,000 unique medical reports to stress-test the Distributed Map.
"""
import argparse
import random

import boto3
from faker import Faker


class LoadTester:
    def __init__(self, bucket_name):
        self.s3 = boto3.client('s3')
        self.fake = Faker()
        self.bucket = bucket_name

    def generate_report(self):
        """Creates a complex synthetic medical report."""
        name = self.fake.name()
        age = random.randint(25, 80)
        clinical_notes = self.fake.paragraph(nb_sentences=15)

        report = f"""
        ATTENDING PHYSICIAN STATEMENT
        PATIENT: {name} | AGE: {age}
        -----------------------------------
        DIAGNOSIS: {random.choice(['Hypertension', 'Type 2 Diabetes', 'CAD', 'Stable'])}
        NOTES: {clinical_notes}
        MEDICATIONS: {self.fake.words(nb=5)}
        """
        return report, name.replace(" ", "_")

    def run_test(self, count):
        print(f"📦 Generating {count} reports for bucket: {self.bucket}...")
        for i in range(count):
            content, name = self.generate_report()
            key = f"uploads/{name}_{i}.txt"
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=content)
            if i % 100 == 0:
                print(f"✅ Uploaded {i} reports...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--bucket", required=True, help="Target S3 Ingest Bucket")
    args = parser.parse_args()

    tester = LoadTester(args.bucket)
    tester.run_test(args.count)
