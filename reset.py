"""
Reset LocalStack environment by deleting all resources and optionally restarting the container.
Use this to get a clean slate for testing.
"""
import sys
import time
import subprocess

from common import CONTAINER_NAME, ENDPOINT, REGION, client


def reset_s3():
    """Delete all S3 buckets."""
    s3 = client("s3")
    try:
        buckets = s3.list_buckets()["Buckets"]
        for bucket in buckets:
            name = bucket["Name"]
            print(f"Deleting S3 bucket: {name}")
            try:
                # Delete all objects first
                objects = s3.list_objects_v2(Bucket=name)
                if "Contents" in objects:
                    for obj in objects["Contents"]:
                        s3.delete_object(Bucket=name, Key=obj["Key"])
                # Delete bucket
                s3.delete_bucket(Bucket=name)
            except Exception as e:
                print(f"  Error deleting {name}: {e}")
    except Exception as e:
        print(f"Error listing buckets: {e}")


def reset_ec2():
    """Delete all EC2 instances and security groups."""
    ec2 = client("ec2")
    try:
        # Terminate instances
        instances = ec2.describe_instances()
        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id = instance["InstanceId"]
                state = instance["State"]["Name"]
                if state != "terminated":
                    print(f"Terminating EC2 instance: {instance_id}")
                    ec2.terminate_instances(InstanceIds=[instance_id])

        # Delete security groups (after instances are gone)
        time.sleep(2)
        sgs = ec2.describe_security_groups()
        for sg in sgs["SecurityGroups"]:
            sg_id = sg["GroupId"]
            name = sg["GroupName"]
            if name != "default":
                print(f"Deleting security group: {name} ({sg_id})")
                try:
                    ec2.delete_security_group(GroupId=sg_id)
                except Exception as e:
                    print(f"  Error deleting {name}: {e}")

        # Delete VPCs (except default)
        vpcs = ec2.describe_vpcs()
        for vpc in vpcs["Vpcs"]:
            vpc_id = vpc["VpcId"]
            if not vpc["IsDefault"]:
                print(f"Deleting VPC: {vpc_id}")
                try:
                    # Delete subnets first
                    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
                    for subnet in subnets["Subnets"]:
                        ec2.delete_subnet(SubnetId=subnet["SubnetId"])
                    ec2.delete_vpc(VpcId=vpc_id)
                except Exception as e:
                    print(f"  Error deleting {vpc_id}: {e}")
    except Exception as e:
        print(f"Error resetting EC2: {e}")


def reset_iam():
    """Delete all IAM users and policies."""
    iam = client("iam")
    try:
        users = iam.list_users()["Users"]
        for user in users:
            username = user["UserName"]
            print(f"Deleting IAM user: {username}")
            try:
                # Delete inline policies
                policies = iam.list_user_policies(UserName=username)["PolicyNames"]
                for policy in policies:
                    iam.delete_user_policy(UserName=username, PolicyName=policy)
                # Delete access keys
                keys = iam.list_access_keys(UserName=username)["AccessKeyMetadata"]
                for key in keys:
                    iam.delete_access_key(UserName=username, AccessKeyId=key["AccessKeyId"])
                # Delete user
                iam.delete_user(UserName=username)
            except Exception as e:
                print(f"  Error deleting {username}: {e}")
    except Exception as e:
        print(f"Error resetting IAM: {e}")


def restart_container():
    """Optionally restart the Docker container."""
    response = input(f"\nRestart Docker container '{CONTAINER_NAME}'? (y/n): ").lower()
    if response == "y":
        print(f"Restarting container {CONTAINER_NAME}...")
        subprocess.run(["docker", "restart", CONTAINER_NAME], check=True)
        time.sleep(5)
        print("Container restarted.")


if __name__ == "__main__":
    print("=== CloudTarget Lab Reset ===")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Region: {REGION}\n")
    
    response = input("This will DELETE ALL resources in LocalStack. Continue? (y/n): ").lower()
    if response != "y":
        print("Aborted.")
        sys.exit(0)

    print("\nResetting LocalStack resources...\n")
    reset_s3()
    reset_ec2()
    reset_iam()
    print("\n✓ Reset complete.")
    
    restart_container()
    print("\nRun `python seed.py` to re-populate with test resources.")
