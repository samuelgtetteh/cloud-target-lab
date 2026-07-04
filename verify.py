"""
Verify that all seeded resources exist AND are configured with the exact
security properties the lab depends on (public bucket really public, insecure
SG really open, admin policy really unscoped, etc). Exits non-zero if
anything is missing or misconfigured, so this can gate a "seed -> verify ->
run scanner" pipeline.
"""
import json

from common import ENDPOINT, REGION, client

failures = []


def fail(message):
    print(f"  ✗ {message}")
    failures.append(message)


def ok(message):
    print(f"  ✓ {message}")


def verify_s3():
    """Verify S3 buckets exist with the expected access policy."""
    print("\n📦 S3 Buckets:")
    s3 = client("s3")
    bucket_names = {b["Name"] for b in s3.list_buckets()["Buckets"]}

    if "acme-internal-backups" not in bucket_names:
        fail("acme-internal-backups (MISSING)")
    else:
        try:
            s3.get_bucket_policy(Bucket="acme-internal-backups")
            fail("acme-internal-backups has a bucket policy but should be private")
        except s3.exceptions.from_code("NoSuchBucketPolicy"):
            ok("acme-internal-backups exists and has no public policy (private, as expected)")

    if "acme-public-uploads" not in bucket_names:
        fail("acme-public-uploads (MISSING)")
    else:
        try:
            policy = s3.get_bucket_policy(Bucket="acme-public-uploads")
            statements = json.loads(policy["Policy"])["Statement"]
            is_public = any(
                s.get("Effect") == "Allow" and s.get("Principal") == "*" and "s3:GetObject" in s.get("Action", [])
                for s in statements
            )
            if is_public:
                ok("acme-public-uploads exists with public-read policy (intentionally insecure, as expected)")
            else:
                fail("acme-public-uploads exists but its policy does not grant public read")
        except s3.exceptions.from_code("NoSuchBucketPolicy"):
            fail("acme-public-uploads exists but has no public-read policy")


def verify_ec2():
    """Verify EC2 instances, and that each security group's rules match its intended posture."""
    print("\n🖥️  EC2 Resources:")
    ec2 = client("ec2")

    sgs = {sg["GroupName"]: sg for sg in ec2.describe_security_groups()["SecurityGroups"]}

    def has_open_ingress(sg, port, cidr="0.0.0.0/0"):
        for perm in sg.get("IpPermissions", []):
            if perm.get("FromPort") == port and perm.get("ToPort") == port:
                if any(r["CidrIp"] == cidr for r in perm.get("IpRanges", [])):
                    return True
        return False

    if "sg-insecure-ssh" not in sgs:
        fail("sg-insecure-ssh (MISSING)")
    elif has_open_ingress(sgs["sg-insecure-ssh"], 22):
        ok("sg-insecure-ssh has SSH open to 0.0.0.0/0 (intentionally insecure, as expected)")
    else:
        fail("sg-insecure-ssh exists but SSH is NOT open to 0.0.0.0/0 (expected finding is missing)")

    if "sg-secure-web" not in sgs:
        fail("sg-secure-web (MISSING)")
    else:
        if has_open_ingress(sgs["sg-secure-web"], 22):
            fail("sg-secure-web has SSH open to 0.0.0.0/0 (should be restricted)")
        else:
            ok("sg-secure-web has SSH restricted (not open to 0.0.0.0/0), as expected")
        if has_open_ingress(sgs["sg-secure-web"], 443):
            ok("sg-secure-web has HTTPS open to 0.0.0.0/0, as expected")
        else:
            fail("sg-secure-web does not expose HTTPS publicly")

    instances_by_name = {}
    for reservation in ec2.describe_instances()["Reservations"]:
        for instance in reservation["Instances"]:
            tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
            name = tags.get("Name", "Unnamed")
            if instance["State"]["Name"] != "terminated":
                instances_by_name[name] = instance

    def uses_security_group(instance, group_name):
        return any(sg["GroupName"] == group_name for sg in instance.get("SecurityGroups", []))

    if "legacy-jump-box" not in instances_by_name:
        fail("legacy-jump-box (MISSING)")
    elif uses_security_group(instances_by_name["legacy-jump-box"], "sg-insecure-ssh"):
        ok("legacy-jump-box uses sg-insecure-ssh, as expected")
    else:
        fail("legacy-jump-box exists but is not attached to sg-insecure-ssh")

    if "web-frontend" not in instances_by_name:
        fail("web-frontend (MISSING)")
    elif uses_security_group(instances_by_name["web-frontend"], "sg-secure-web"):
        ok("web-frontend uses sg-secure-web, as expected")
    else:
        fail("web-frontend exists but is not attached to sg-secure-web")


def verify_iam():
    """Verify IAM users exist with policies that grant exactly the intended scope."""
    print("\n👤 IAM Users:")
    iam = client("iam")
    user_names = {u["UserName"] for u in iam.list_users()["Users"]}

    def get_policy_statements(username, policy_name):
        doc = iam.get_user_policy(UserName=username, PolicyName=policy_name)["PolicyDocument"]
        return doc["Statement"]

    if "svc-legacy-app" not in user_names:
        fail("svc-legacy-app (MISSING)")
    else:
        try:
            statements = get_policy_statements("svc-legacy-app", "AdminEquivalent")
            is_admin = any(s.get("Action") == "*" and s.get("Resource") == "*" for s in statements)
            if is_admin:
                ok("svc-legacy-app has an admin-equivalent policy (intentionally insecure, as expected)")
            else:
                fail("svc-legacy-app's AdminEquivalent policy is not actually unscoped")
        except iam.exceptions.NoSuchEntityException:
            fail("svc-legacy-app exists but has no AdminEquivalent policy")

    if "alice-analyst" not in user_names:
        fail("alice-analyst (MISSING)")
    else:
        try:
            statements = get_policy_statements("alice-analyst", "ReadOnlyReports")
            is_scoped = all(s.get("Action") != "*" for s in statements)
            if is_scoped:
                ok("alice-analyst has a scoped read-only policy, as expected")
            else:
                fail("alice-analyst's ReadOnlyReports policy is unexpectedly unscoped")
        except iam.exceptions.NoSuchEntityException:
            fail("alice-analyst exists but has no ReadOnlyReports policy")


def verify_connectivity():
    """Verify LocalStack is reachable."""
    print("\n🔗 Connectivity:")
    try:
        import urllib.request
        urllib.request.urlopen(f"{ENDPOINT}/_localstack/health", timeout=5)
        ok(f"LocalStack is reachable at {ENDPOINT}")
    except Exception as e:
        fail(f"Cannot reach LocalStack: {e}")


if __name__ == "__main__":
    import sys

    print("=== CloudTarget Lab Verification ===")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Region: {REGION}")

    verify_connectivity()
    if not failures:
        verify_s3()
        verify_ec2()
        verify_iam()

    if failures:
        print(f"\n✗ Verification failed: {len(failures)} issue(s) found.")
        sys.exit(1)

    print("\n✓ Verification complete. All resources match expected configuration.")
