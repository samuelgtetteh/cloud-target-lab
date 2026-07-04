# CloudTarget Lab - Troubleshooting Guide

## Quick Start Issues

### Container won't start
**Error:** `docker compose up -d` fails or container exits immediately

**Solutions:**
```bash
# Check Docker daemon is running
docker ps

# Check container logs
docker logs cloud-target-lab

# Rebuild the compose file
docker compose down
docker compose up -d

# Check available disk space
docker system df
```

### LocalStack is slow or unresponsive
**Error:** `seed.py` times out or very slow responses

**Solutions:**
```bash
# Give LocalStack more time to initialize
# Wait 30+ seconds after docker compose up -d

# Check container resource usage
docker stats cloud-target-lab

# Increase Docker memory allocation (Docker Desktop settings)
# Default: 2GB → Recommended: 4GB+ for LocalStack

# Restart container with fresh state
docker restart cloud-target-lab
```

### Python dependencies missing
**Error:** `ModuleNotFoundError: No module named 'boto3'`

**Solution:**
```bash
pip install -r requirements.txt
```

## Connection Issues

### Cannot connect to LocalStack
**Error:** `ConnectionRefusedError` or `URLError`

**Diagnosis:**
```bash
# Check container is running
docker ps | grep cloud-target-lab

# Test connectivity
curl http://localhost:4566/_localstack/health

# Run status check
python status.py
```

**Solutions:**
1. Ensure Docker container is running: `docker compose up -d`
2. Wait for LocalStack to be ready (check logs): `docker logs cloud-target-lab`
3. Check if port 4566 is already in use: `netstat -ano | findstr :4566`
4. Modify port in `docker-compose.yml` if needed

### Wrong endpoint/credentials
**Error:** Boto3 returns authentication errors

**Solution:**
Check `.env` file matches docker-compose environment:
```ini
LOCALSTACK_ENDPOINT=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

## Seeding Issues

### Resources already exist (EntityAlreadyExists)
**Error:** `seed.py` fails on second run

**Solution (automatic now):**
Script now handles existing resources gracefully. Just run again:
```bash
python seed.py
```

**Manual fix if still occurs:**
```bash
# Full reset
python reset.py

# Or selective cleanup
python cleanup.py
```

### Only some resources created
**Diagnosis:**
```bash
python verify.py
```

**Solutions:**
- Check Docker logs for errors: `docker logs cloud-target-lab`
- Ensure LocalStack has all required services enabled in `docker-compose.yml`:
  - `SERVICES=s3,ec2,iam,sts`

## Resource Issues

### Cannot find created resources
**Diagnosis:**
```bash
python status.py    # See resource counts
python verify.py    # Check specific resources
```

**Solution:**
Verify endpoint and credentials match:
```bash
# Edit .env if needed
echo "LOCALSTACK_ENDPOINT=http://localhost:4566" > .env
```

## Performance Optimization

### Slow API calls
1. Check LocalStack is healthy: `docker logs cloud-target-lab | tail -20`
2. Increase Docker resource limits
3. Close other resource-heavy applications

### Cleanup disk space
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Check volume size
du -sh volume/
```

## Advanced Troubleshooting

### Enable debug mode
Edit `docker-compose.yml`:
```yaml
environment:
  - DEBUG=1  # Set to 1 for verbose logging
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### Check container logs for specific errors
```bash
# Last 50 lines
docker logs --tail 50 cloud-target-lab

# Follow logs in real-time
docker logs -f cloud-target-lab

# Since specific time
docker logs --since 2026-07-04T10:00:00 cloud-target-lab
```

### Inspect resource state directly
```bash
# List all S3 buckets
python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:4566', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
print(s3.list_buckets())
"

# List all EC2 instances
python -c "
import boto3
ec2 = boto3.client('ec2', endpoint_url='http://localhost:4566', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
print(ec2.describe_instances())
"
```

## Common Scanner Issues

### Scanner can't connect
**Solution:** Ensure scanner uses correct endpoint:
```python
client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',  # LocalStack endpoint
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)
```

### Scanner doesn't detect intentionally insecure resources
1. Verify resources were seeded: `python verify.py`
2. Check resource configurations match expected vulnerabilities
3. Ensure scanner is checking for the right issues

## Getting Help

### Useful commands
```bash
python status.py       # Overall environment status
python verify.py       # Validate seeded resources
docker logs -f cloud-target-lab  # Live container logs
docker ps             # Check container status
```

### Check LocalStack documentation
- https://docs.localstack.cloud/
- https://github.com/localstack/localstack

### Debug checklist
- [ ] Docker is running: `docker ps`
- [ ] Container is healthy: `docker logs cloud-target-lab`
- [ ] Can reach endpoint: `curl http://localhost:4566/_localstack/health`
- [ ] Dependencies installed: `pip list | grep boto`
- [ ] .env file is correct: `cat .env`
- [ ] Resources are seeded: `python verify.py`
