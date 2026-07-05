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


# --- Shared teardown primitives ------------------------------------------
# reset.py (delete everything) and cleanup.py (delete one named resource)
# both need these, so they live here in one place rather than being
# reimplemented — and slightly differently — in each script. They perform
# the AWS calls and raise on error; callers own the messaging and any
# per-resource error handling.

def delete_s3_bucket(s3, bucket_name):
    """Empty a bucket (paginated, so >1000 objects are fully removed) then
    delete the bucket itself."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get("Contents", []):
            s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
    s3.delete_bucket(Bucket=bucket_name)


def terminate_ec2_instance(ec2, instance_id):
    """Terminate a single EC2 instance."""
    ec2.terminate_instances(InstanceIds=[instance_id])


def delete_iam_user(iam, username):
    """Remove a user's inline policies and access keys (required before an IAM
    user can be deleted), then delete the user."""
    for policy in iam.list_user_policies(UserName=username)["PolicyNames"]:
        iam.delete_user_policy(UserName=username, PolicyName=policy)
    for key in iam.list_access_keys(UserName=username)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=username, AccessKeyId=key["AccessKeyId"])
    iam.delete_user(UserName=username)
