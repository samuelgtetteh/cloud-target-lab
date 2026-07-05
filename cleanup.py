"""
Selectively clean up specific resources from LocalStack.
Use this to remove particular resources without a full reset.
"""
import sys

from common import (
    ENDPOINT,
    client,
    delete_iam_user,
    delete_s3_bucket,
    terminate_ec2_instance,
)


def cleanup_s3_bucket(bucket_name):
    """Delete a specific S3 bucket and all its contents."""
    s3 = client("s3")
    try:
        delete_s3_bucket(s3, bucket_name)
        print(f"✓ Deleted bucket: {bucket_name}")
    except Exception as e:
        print(f"✗ Error deleting bucket {bucket_name}: {e}")


def cleanup_ec2_instance(instance_id):
    """Terminate a specific EC2 instance."""
    ec2 = client("ec2")
    try:
        terminate_ec2_instance(ec2, instance_id)
        print(f"✓ Terminated instance: {instance_id}")
    except Exception as e:
        print(f"✗ Error terminating instance {instance_id}: {e}")


def cleanup_iam_user(username):
    """Delete a specific IAM user and all policies."""
    iam = client("iam")
    try:
        delete_iam_user(iam, username)
        print(f"✓ Deleted user: {username}")
    except Exception as e:
        print(f"✗ Error deleting user {username}: {e}")


def list_resources():
    """List all available resources."""
    print("\n📋 Available Resources to Clean Up:\n")
    
    # S3 Buckets
    print("S3 Buckets:")
    s3 = client("s3")
    try:
        buckets = s3.list_buckets()["Buckets"]
        if buckets:
            for i, bucket in enumerate(buckets, 1):
                print(f"  {i}. {bucket['Name']}")
        else:
            print("  (none)")
    except Exception as e:
        print(f"  Error: {e}")
    
    # EC2 Instances
    print("\nEC2 Instances:")
    ec2 = client("ec2")
    try:
        instances = ec2.describe_instances()
        instance_num = 1
        for reservation in instances["Reservations"]:
            for instance in reservation["Instances"]:
                tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                name = tags.get("Name", "Unnamed")
                print(f"  {instance_num}. {name} ({instance['InstanceId']})")
                instance_num += 1
        if instance_num == 1:
            print("  (none)")
    except Exception as e:
        print(f"  Error: {e}")
    
    # IAM Users
    print("\nIAM Users:")
    iam = client("iam")
    try:
        users = iam.list_users()["Users"]
        if users:
            for i, user in enumerate(users, 1):
                print(f"  {i}. {user['UserName']}")
        else:
            print("  (none)")
    except Exception as e:
        print(f"  Error: {e}")


def interactive_cleanup():
    """Interactive cleanup menu."""
    print("\n=== CloudTarget Lab Cleanup ===")
    print(f"Endpoint: {ENDPOINT}\n")
    
    while True:
        print("\nCleanup Options:")
        print("  1. List all resources")
        print("  2. Delete S3 bucket")
        print("  3. Delete EC2 instance")
        print("  4. Delete IAM user")
        print("  5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            list_resources()
        elif choice == "2":
            bucket = input("Enter bucket name to delete: ").strip()
            if bucket:
                confirm = input(f"Delete bucket '{bucket}'? (y/n): ").lower()
                if confirm == "y":
                    cleanup_s3_bucket(bucket)
        elif choice == "3":
            instance_id = input("Enter instance ID to terminate: ").strip()
            if instance_id:
                confirm = input(f"Terminate instance '{instance_id}'? (y/n): ").lower()
                if confirm == "y":
                    cleanup_ec2_instance(instance_id)
        elif choice == "4":
            username = input("Enter username to delete: ").strip()
            if username:
                confirm = input(f"Delete user '{username}'? (y/n): ").lower()
                if confirm == "y":
                    cleanup_iam_user(username)
        elif choice == "5":
            print("Exiting.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command-line mode
        if sys.argv[1] == "--list":
            list_resources()
        elif sys.argv[1] == "--s3" and len(sys.argv) > 2:
            cleanup_s3_bucket(sys.argv[2])
        elif sys.argv[1] == "--instance" and len(sys.argv) > 2:
            cleanup_ec2_instance(sys.argv[2])
        elif sys.argv[1] == "--user" and len(sys.argv) > 2:
            cleanup_iam_user(sys.argv[2])
        else:
            print("Usage:")
            print("  python cleanup.py              - Interactive mode")
            print("  python cleanup.py --list       - List all resources")
            print("  python cleanup.py --s3 BUCKET  - Delete S3 bucket")
            print("  python cleanup.py --instance ID - Terminate EC2 instance")
            print("  python cleanup.py --user USER  - Delete IAM user")
    else:
        # Interactive mode
        interactive_cleanup()
