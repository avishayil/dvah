# Sandbox image for executing user-edited lab code (DVAH_RUNNER=docker).
# Run with: --network none --read-only --user 65534:65534 --memory 512m --cpus 1
#           --pids-limit 128 --tmpfs /tmp -v <session>:/work
FROM python:3.11-slim

# Install the dvah package (harness + webapi report plugin). The build context is the
# repo root: `docker build -f webapi/runner.Dockerfile -t dvah-runner:latest .`
WORKDIR /opt/dvah
COPY pyproject.toml README.md ./
COPY dvah ./dvah
RUN pip install --no-cache-dir -e ".[dev]"

# Drop privileges; the workspace is bind-mounted read-write at /work at run time.
USER 65534:65534
WORKDIR /work
ENTRYPOINT []
