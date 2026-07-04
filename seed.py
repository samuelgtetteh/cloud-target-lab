"""
Populates the LocalStack instance with fake AWS resources — a mix of
deliberately insecure ones (public bucket, wide-open security group,
over-privileged IAM user) and properly configured ones, so a cloud scanner
being tested against this has genuine, varied findings to detect rather than
an all-or-nothing test fixture.

Run this after `docker-compose up -d` and give LocalStack a few seconds to
be ready. Safe to run multiple times — every resource is created idempotently.
"""
import json
import os
import time

from common import ENDPOINT, client

VPC_NAME = "cloud-target-lab-vpc"


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

    try:
        s3.create_bucket(Bucket="acme-internal-backups")
        print("Created S3 bucket: acme-internal-backups (private)")
    except (s3.exceptions.BucketAlreadyExists, s3.exceptions.BucketAlreadyOwnedByYou):
        print("S3 bucket acme-internal-backups already exists")

    try:
        s3.create_bucket(Bucket="acme-public-uploads")
        print("Created S3 bucket: acme-public-uploads")
    except (s3.exceptions.BucketAlreadyExists, s3.exceptions.BucketAlreadyOwnedByYou):
        print("S3 bucket acme-public-uploads already exists")

    public_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow", "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::acme-public-uploads/*",
        }],
    }
    s3.put_bucket_policy(Bucket="acme-public-uploads", Policy=json.dumps(public_policy))
    print("Set public-read policy on acme-public-uploads (PUBLIC READ - intentionally insecure)")


def get_or_create_vpc(ec2):
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Name", "Values": [VPC_NAME]}])["Vpcs"]
    if vpcs:
        return vpcs[0]["VpcId"]
    vpc_id = ec2.create_vpc(CidrBlock="10.10.0.0/16")["Vpc"]["VpcId"]
    ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": VPC_NAME}])
    return vpc_id


def get_or_create_security_group(ec2, vpc_id, name, description, ip_permissions):
    sgs = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}, {"Name": "group-name", "Values": [name]}]
    )["SecurityGroups"]
    if sgs:
        return sgs[0]["GroupId"]

    group_id = ec2.create_security_group(GroupName=name, Description=description, VpcId=vpc_id)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=ip_permissions)
    return group_id


def get_or_create_instance(ec2, name, security_group_id, ami_id):
    existing = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [name]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
    ])
    for reservation in existing["Reservations"]:
        for instance in reservation["Instances"]:
            return instance["InstanceId"], False

    instance = ec2.run_instances(
        ImageId=ami_id, MinCount=1, MaxCount=1, InstanceType="t2.micro",
        SecurityGroupIds=[security_group_id],
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": name}]}],
    )["Instances"][0]
    return instance["InstanceId"], True


def seed_ec2():
    ec2 = client("ec2")

    vpc_id = get_or_create_vpc(ec2)

    insecure_sg = get_or_create_security_group(
        ec2, vpc_id, "sg-insecure-ssh", "Overly permissive SSH access",
        ip_permissions=[{
            "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
        }],
    )
    print(f"Security group sg-insecure-ssh ({insecure_sg}) - SSH open to 0.0.0.0/0 (intentionally insecure)")

    secure_sg = get_or_create_security_group(
        ec2, vpc_id, "sg-secure-web", "Web server, restricted admin access",
        ip_permissions=[
            {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "203.0.113.10/32"}]},
        ],
    )
    print(f"Security group sg-secure-web ({secure_sg}) - HTTPS public, SSH restricted to one IP")

    images = ec2.describe_images()["Images"]
    ami_id = images[0]["ImageId"] if images else "ami-00000000"

    _, created = get_or_create_instance(ec2, "legacy-jump-box", insecure_sg, ami_id)
    print(f"{'Launched' if created else 'Found existing'} EC2 instance 'legacy-jump-box' using sg-insecure-ssh")

    _, created = get_or_create_instance(ec2, "web-frontend", secure_sg, ami_id)
    print(f"{'Launched' if created else 'Found existing'} EC2 instance 'web-frontend' using sg-secure-web")


def seed_iam():
    iam = client("iam")

    try:
        iam.create_user(UserName="svc-legacy-app")
        iam.put_user_policy(
            UserName="svc-legacy-app", PolicyName="AdminEquivalent",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
            }),
        )
        print("Created IAM user svc-legacy-app with an admin-equivalent inline policy (intentionally insecure)")
    except iam.exceptions.EntityAlreadyExistsException:
        print("IAM user svc-legacy-app already exists")

    try:
        iam.create_user(UserName="alice-analyst")
        iam.put_user_policy(
            UserName="alice-analyst", PolicyName="ReadOnlyReports",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"], "Resource": "*"}],
            }),
        )
        print("Created IAM user alice-analyst with a scoped read-only policy")
    except iam.exceptions.EntityAlreadyExistsException:
        print("IAM user alice-analyst already exists")


def env_flag(name, default=True):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes")


if __name__ == "__main__":
    wait_for_localstack()
    if env_flag("SEED_S3"):
        seed_s3()
    else:
        print("Skipping S3 (SEED_S3=false)")
    if env_flag("SEED_EC2"):
        seed_ec2()
    else:
        print("Skipping EC2 (SEED_EC2=false)")
    if env_flag("SEED_IAM"):
        seed_iam()
    else:
        print("Skipping IAM (SEED_IAM=false)")
    print("\nSeeding complete.")
