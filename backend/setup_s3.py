#!/usr/bin/env python3
"""
Upload trade dataset and model artifacts to S3.
Run once after training: python setup_s3.py
"""

import boto3
import os
import sys

BUCKET = os.getenv("S3_BUCKET", "agroshield-trade-data")
REGION = os.getenv("AWS_REGION", "ap-south-1")

s3 = boto3.client("s3", region_name=REGION)


def create_bucket():
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET)
        else:
            s3.create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        print(f"✓ Created S3 bucket: {BUCKET}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"⚠ Bucket already exists: {BUCKET}")
    except Exception as exc:
        print(f"Bucket create error (may already exist): {exc}")


def upload(local_path, s3_key):
    if not os.path.exists(local_path):
        print(f"⚠ File not found: {local_path}")
        return
    print(f"Uploading {local_path} → s3://{BUCKET}/{s3_key}")
    s3.upload_file(local_path, BUCKET, s3_key)
    print(f"✓ Uploaded: {s3_key}")


if __name__ == "__main__":
    create_bucket()

    # Upload trade dataset
    upload("data/trade_dataset.csv", "raw-data/trade_dataset.csv")

    # Upload model artifacts (if they exist)
    upload("data/risk_model.pkl",      "model-artifacts/risk_model.pkl")
    upload("data/encoders.pkl",        "model-artifacts/encoders.pkl")
    upload("data/feature_columns.pkl", "model-artifacts/feature_columns.pkl")

    print("\nS3 setup complete. Files available at:")
    print(f"  s3://{BUCKET}/raw-data/trade_dataset.csv")
    print(f"  s3://{BUCKET}/model-artifacts/risk_model.pkl")
