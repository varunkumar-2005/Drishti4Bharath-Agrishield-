#!/usr/bin/env python3
"""
Create DynamoDB tables for AgroShield.
Run once before deploying: python setup_dynamo.py
"""

import boto3
import os

REGION = os.getenv("AWS_REGION", "ap-south-1")
client = boto3.client("dynamodb", region_name=REGION)

TABLES = [
    {
        "TableName": "agroshield-events",
        "KeySchema": [{"AttributeName": "event_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "event_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "agroshield-advisories",
        "KeySchema": [{"AttributeName": "advisory_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "advisory_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "agroshield-chat-logs",
        "KeySchema": [{"AttributeName": "chat_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "chat_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
]

for table in TABLES:
    try:
        client.create_table(**table)
        print(f"✓ Created table: {table['TableName']}")
    except client.exceptions.ResourceInUseException:
        print(f"⚠ Table already exists: {table['TableName']}")
    except Exception as exc:
        print(f"✗ Failed to create {table['TableName']}: {exc}")

print("DynamoDB setup complete.")
