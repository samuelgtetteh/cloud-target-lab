"""
Display a comprehensive status dashboard for the LocalStack environment.
Shows resource counts, connectivity, and configuration.
"""
from common import ENDPOINT, REGION, client


def get_status():
    """Collect status information from all services."""
    status = {
        "endpoint": ENDPOINT,
        "region": REGION,
        "connected": False,
        "s3": {"buckets": 0, "total_objects": 0},
        "ec2": {"instances": 0, "security_groups": 0, "vpcs": 0},
        "iam": {"users": 0, "policies": 0},
        "errors": []
    }
    
    # Test connectivity
    try:
        import urllib.request
        urllib.request.urlopen(f"{ENDPOINT}/_localstack/health", timeout=5)
        status["connected"] = True
    except Exception as e:
        status["errors"].append(f"Connectivity: {e}")
        return status
    
    # S3 Status
    try:
        s3 = client("s3")
        buckets = s3.list_buckets()["Buckets"]
        status["s3"]["buckets"] = len(buckets)
        for bucket in buckets:
            try:
                objs = s3.list_objects_v2(Bucket=bucket["Name"])
                if "Contents" in objs:
                    status["s3"]["total_objects"] += len(objs["Contents"])
            except Exception as e:
                status["errors"].append(f"S3 ({bucket['Name']}): {e}")
    except Exception as e:
        status["errors"].append(f"S3: {e}")
    
    # EC2 Status
    try:
        ec2 = client("ec2")
        instances = ec2.describe_instances()
        instance_count = sum(len(r["Instances"]) for r in instances["Reservations"])
        status["ec2"]["instances"] = instance_count
        
        sgs = ec2.describe_security_groups()
        status["ec2"]["security_groups"] = len(sgs["SecurityGroups"])
        
        vpcs = ec2.describe_vpcs()
        status["ec2"]["vpcs"] = len(vpcs["Vpcs"])
    except Exception as e:
        status["errors"].append(f"EC2: {e}")
    
    # IAM Status
    try:
        iam = client("iam")
        users = iam.list_users()["Users"]
        status["iam"]["users"] = len(users)
        
        for user in users:
            policies = iam.list_user_policies(UserName=user["UserName"])["PolicyNames"]
            status["iam"]["policies"] += len(policies)
    except Exception as e:
        status["errors"].append(f"IAM: {e}")
    
    return status


def print_dashboard(status):
    """Print a formatted status dashboard."""
    print("\n" + "="*50)
    print("  CloudTarget Lab - Status Dashboard")
    print("="*50)
    
    print(f"\n🌐 Connection Status:")
    print(f"  Endpoint: {status['endpoint']}")
    print(f"  Region: {status['region']}")
    conn_status = "🟢 CONNECTED" if status["connected"] else "🔴 DISCONNECTED"
    print(f"  Status: {conn_status}")
    
    if not status["connected"]:
        print("\n⚠️  Cannot connect to LocalStack. Is it running?")
        print("  Run: docker compose up -d")
        return
    
    print(f"\n📦 S3 Resources:")
    print(f"  Buckets: {status['s3']['buckets']}")
    print(f"  Objects: {status['s3']['total_objects']}")
    
    print(f"\n🖥️  EC2 Resources:")
    print(f"  Instances: {status['ec2']['instances']}")
    print(f"  Security Groups: {status['ec2']['security_groups']}")
    print(f"  VPCs: {status['ec2']['vpcs']}")
    
    print(f"\n👤 IAM Resources:")
    print(f"  Users: {status['iam']['users']}")
    print(f"  Policies: {status['iam']['policies']}")
    
    if status["errors"]:
        print(f"\n⚠️  Errors:")
        for error in status["errors"]:
            print(f"  - {error}")
    
    print("\n" + "="*50 + "\n")


def show_usage():
    """Show available commands."""
    print("\n📋 Available Commands:")
    print("  python seed.py       - Populate with test resources")
    print("  python verify.py     - Validate seeded resources")
    print("  python status.py     - Show this dashboard")
    print("  python reset.py      - Delete all resources")
    print("  python cleanup.py    - Clean up specific resources")


if __name__ == "__main__":
    status = get_status()
    print_dashboard(status)
    show_usage()
