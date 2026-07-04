"""Shared LocalStack configuration used by every script in this lab."""
import os
import sys
from dotenv import load_dotenv

import boto3

# Scripts print emoji status markers; force UTF-8 so that works on Windows
# consoles, which otherwise default to a codepage that can't encode them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_REGION", "us-east-1")
CREDS = {
    "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "test"),
    "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
}
CONTAINER_NAME = os.getenv("LOCALSTACK_DOCKER_NAME", "cloud-target-lab")


def client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, region_name=REGION, **CREDS)
