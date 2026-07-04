# CloudTarget Lab - Quick Reference

## Environment Setup

### Initial Setup
```bash
docker compose up -d          # Start LocalStack container
pip install -r requirements.txt # Install dependencies
python seed.py               # Populate with test resources
```

### Verify Everything Works
```bash
python status.py             # View environment dashboard
python verify.py             # Validate all resources exist
```

---

## Utility Scripts

### 📊 `status.py` - Environment Dashboard
Shows real-time status of all resources and connection health.

```bash
python status.py
```

**Output:**
- Connection status to LocalStack
- S3 resource count
- EC2 instances & security groups count
- IAM users & policies count
- Any errors or warnings

---

### ✅ `verify.py` - Resource Validation
Checks that all expected resources exist and are configured correctly.

```bash
python verify.py
```

**Verifies:**
- ✓ S3 buckets exist with correct policies
- ✓ EC2 instances are running
- ✓ Security groups are configured
- ✓ IAM users and policies are in place
- ✓ LocalStack connectivity

---

### 🔄 `reset.py` - Full Environment Reset
Deletes ALL resources and optionally restarts the container.

```bash
python reset.py
```

**Deletes:**
- All S3 buckets and objects
- All EC2 instances and security groups
- All VPCs
- All IAM users and policies

⚠️ **This is destructive** - You'll be prompted for confirmation.

---

### 🧹 `cleanup.py` - Selective Resource Removal
Interactive mode to delete specific resources without full reset.

```bash
python cleanup.py              # Interactive menu
python cleanup.py --list       # List all resources
python cleanup.py --s3 BUCKET  # Delete S3 bucket
python cleanup.py --instance ID # Terminate EC2 instance
python cleanup.py --user USER   # Delete IAM user
```

**Interactive Options:**
1. List all resources
2. Delete S3 bucket
3. Delete EC2 instance
4. Delete IAM user
5. Exit

---

## Configuration Files

### `.env` - Environment Configuration
Centralized configuration for all scripts:

```ini
LOCALSTACK_ENDPOINT=http://localhost:4566
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
LOCALSTACK_DOCKER_NAME=cloud-target-lab
```

**Edit this to:**
- Change LocalStack endpoint or port
- Use different AWS credentials
- Modify region
- Update container name

### `docker-compose.yml` - Container Configuration
Enhanced with health checks and logging:

**Features:**
- Health checks every 10 seconds
- Automatic log rotation (max 10MB per file, 3 files)
- Docker socket mounting for advanced operations
- Startup period of 15 seconds before health check

---

## Common Workflows

### Complete Fresh Start
```bash
python reset.py
docker restart cloud-target-lab
python seed.py
python verify.py
```

### Check Environment Health
```bash
python status.py
python verify.py
docker logs -f cloud-target-lab
```

### Remove Just S3 Resources
```bash
python cleanup.py
# Choose option 2
# Enter bucket names
```

### Debug Connectivity
```bash
curl http://localhost:4566/_localstack/health
python status.py
docker logs cloud-target-lab
```

---

## Troubleshooting

See `TROUBLESHOOTING.md` for detailed solutions to common issues.

**Quick fixes:**
```bash
# Container won't start
docker compose down
docker compose up -d

# Resources missing
python verify.py

# Too many resources (cleanup)
python reset.py

# Slow responses
docker stats cloud-target-lab
```

---

## Seeded Resources

### S3 Buckets
- `acme-internal-backups` (private)
- `acme-public-uploads` (public read - intentionally insecure)

### EC2 Instances
- `legacy-jump-box` (uses sg-insecure-ssh)
- `web-frontend` (uses sg-secure-web)

### Security Groups
- `sg-insecure-ssh` (SSH open to 0.0.0.0/0 - intentionally insecure)
- `sg-secure-web` (HTTPS public, SSH restricted)

### IAM Users
- `svc-legacy-app` (admin-equivalent policy - intentionally insecure)
- `alice-analyst` (read-only S3 policy)

---

## Using with Scanners

Point your security scanner at:
```
Endpoint: http://localhost:4566
Credentials: test / test
Region: us-east-1
```

All AWS SDK clients work against LocalStack with no code changes!

---

## Resources

- LocalStack Docs: https://docs.localstack.cloud/
- AWS SDK (boto3): https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- Repository: https://github.com/samuelgtetteh/cloud-target-lab
