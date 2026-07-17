# Cloud Target Lab — seeder/toolkit image. LocalStack itself runs from docker-compose.yml;
# this image bundles the Python scripts that seed / verify / reset the fake-AWS resources.
# Usage (with LocalStack reachable, e.g. on the host or in the same compose network):
#   docker run --rm -e LOCALSTACK_ENDPOINT=http://host.docker.internal:4566 \
#     ghcr.io/samuelgtetteh/cloud-target-lab:0.1 python seed.py
# Scripts: seed.py (create resources) · verify.py · status.py · reset.py · cleanup.py
FROM python:3.11-slim
LABEL org.opencontainers.image.source="https://github.com/samuelgtetteh/cloud-target-lab"
LABEL org.opencontainers.image.description="Cloud Target Lab seeder — seeds a LocalStack fake-AWS with mixed secure/insecure resources for scanner testing"
LABEL org.opencontainers.image.licenses="Apache-2.0"
WORKDIR /app
RUN pip install --no-cache-dir boto3==1.43.40 python-dotenv==1.2.2
COPY common.py seed.py verify.py status.py reset.py cleanup.py ./
ENV LOCALSTACK_ENDPOINT=http://host.docker.internal:4566
CMD ["python", "seed.py"]
