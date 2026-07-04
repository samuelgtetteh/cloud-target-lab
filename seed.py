"""
Populates the LocalStack instance with fake AWS resources — a mix of
deliberately insecure ones (public bucket, wide-open security group,
over-privileged IAM user) and properly configured ones, so a cloud scanner
being tested against this has genuine, varied findings to detect rather than
an all-or-nothing test fixture.

Run this after `docker-compose up -d` and give LocalStack a few seconds to
be ready.
"""
import json
import time

import boto3

ENDPOINT = "http://localhost:4566"
REGION = "us-east-1"
CREDS = {"aws_access_key_id": "test", "aws_secret_access_key": "test"}


def client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, region_name=REGION, **CREDS)


def wait_for_localstack(timeout=60):
    import urllib.request
    started = time.time()
    while time.time() - started < timeout:
        try:
            urllib.request.urlopen(f"{ENDPOINT}/_localstack/health", timeout=2)
            print("LocalStack is up.")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("LocalStack did not become ready in time.")


def seed_s3():
    s3 = client("s3")

    s3.create_bucket(Bucket="acme-internal-backups")
    print("Created S3 bucket: acme-internal-backups (private)")

    s3.create_bucket(Bucket="acme-public-uploads")
    public_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow", "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::acme-public-uploads/*",
        }],
    }
    s3.put_bucket_policy(Bucket="acme-public-uploads", Policy=json.dumps(public_policy))
    print("Created S3 bucket: acme-public-uploads (PUBLIC READ - intentionally insecure)")


def seed_ec2():
    ec2 = client("ec2")

    vpc = ec2.create_vpc(CidrBlock="10.10.0.0/16")["Vpc"]["VpcId"]

    insecure_sg = ec2.create_security_group(
        GroupName="sg-insecure-ssh", Description="Overly permissive SSH access", VpcId=vpc
    )["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=insecure_sg,
        IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        }],
    )
    print(f"Created security group sg-insecure-ssh ({insecure_sg}) - SSH open to 0.0.0.0/0 (intentionally insecure)")

    secure_sg = ec2.create_security_group(
        GroupName="sg-secure-web", Description="Web server, restricted admin access", VpcId=vpc
    )["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=secure_sg,
        IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "203.0.113.10/32"}]},
        ],
    )
    print(f"Created security group sg-secure-web ({secure_sg}) - HTTPS public, SSH restricted to one IP")

    images = ec2.describe_images()["Images"]
    ami_id = images[0]["ImageId"] if images else "ami-00000000"

    ec2.run_instances(
        ImageId=ami_id, MinCount=1, MaxCount=1, InstanceType="t2.micro",
        SecurityGroupIds=[insecure_sg], TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "legacy-jump-box"}]}
        ],
    )
    print("Launched EC2 instance 'legacy-jump-box' using sg-insecure-ssh")

    ec2.run_instances(
        ImageId=ami_id, MinCount=1, MaxCount=1, InstanceType="t2.micro",
        SecurityGroupIds=[secure_sg], TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "web-frontend"}]}
        ],
    )
    print("Launched EC2 instance 'web-frontend' using sg-secure-web")


def seed_iam():
    iam = client("iam")

    iam.create_user(UserName="svc-legacy-app")
    iam.put_user_policy(
        UserName="svc-legacy-app", PolicyName="AdminEquivalent",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
        }),
    )
    print("Created IAM user svc-legacy-app with an admin-equivalent inline policy (intentionally insecure)")

    iam.create_user(UserName="alice-analyst")
    iam.put_user_policy(
        UserName="alice-analyst", PolicyName="ReadOnlyReports",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"], "Resource": "*"}],
        }),
    )
    print("Created IAM user alice-analyst with a scoped read-only policy")


if __name__ == "__main__":
    wait_for_localstack()
    seed_s3()
    seed_ec2()
    seed_iam()
    print("\nSeeding complete.")
