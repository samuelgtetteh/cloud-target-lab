# Cloud Target Lab

A disposable, Dockerized fake AWS environment for testing cloud security scanners — used to validate [Control Advisor](https://github.com/samuelgtetteh/ai-cybersecurity-portfolio)'s cloud auditing capability (`control-advisor/scanner/cloud_scan.py`) without needing a real AWS account.

Runs [LocalStack](https://github.com/localstack/localstack) (an open-source AWS emulator) and seeds it with a deliberately mixed set of resources — some correctly configured, some intentionally insecure — so a scanner being tested against it has genuine, varied findings to detect rather than an all-or-nothing fixture.

## Seeded resources

| Resource | Configuration |
|---|---|
| S3 bucket `acme-internal-backups` | Private (correctly configured) |
| S3 bucket `acme-public-uploads` | **Public read** (intentionally insecure) |
| Security group `sg-insecure-ssh` | **SSH open to 0.0.0.0/0** (intentionally insecure) |
| Security group `sg-secure-web` | HTTPS public, SSH restricted to one IP (correctly configured) |
| EC2 instance `legacy-jump-box` | Uses the insecure security group |
| EC2 instance `web-frontend` | Uses the secure security group |
| IAM user `svc-legacy-app` | **Admin-equivalent inline policy** (`Action: *`, `Resource: *`) (intentionally insecure) |
| IAM user `alice-analyst` | Scoped read-only policy (correctly configured) |

## Usage

```bash
docker compose up -d
pip install -r requirements.txt
python seed.py
```

Then point a scanner (e.g. Control Advisor's `cloud_scan.py`) at `http://localhost:4566` with dummy credentials (`test`/`test`) — the real AWS SDK works against LocalStack unmodified, so the same scanner code works against a real AWS account later with no changes.

**This is a local testing fixture only.** It runs entirely in Docker on your own machine and does not touch any real cloud account.
