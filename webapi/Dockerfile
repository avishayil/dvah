# DVAH lab API image. Runs the FastAPI app that wraps the harness and executes each
# lab's pytest suite via the default SubprocessRunner — so it needs the dev extra
# (pytest) and the full repo (challenges/tests/docs), not just the base package.
FROM python:3.12.3-slim
WORKDIR /app

RUN pip install --no-cache-dir uv

# Install deps first (better layer caching), then the package.
COPY pyproject.toml README.md ./
COPY dvah ./dvah
COPY challenges ./challenges
COPY services ./services
COPY tests ./tests
COPY docs ./docs
COPY conftest.py ./
RUN uv pip install --system -e ".[dev,services,web]"

# Run as non-root; ephemeral session workspaces live under /tmp (writable).
RUN useradd --create-home app && chown -R app /app
USER app

ENV PYTHONPATH=/app \
    DVAH_RUNNER=subprocess \
    DVAH_CORS_ORIGINS=http://localhost:3000 \
    DVAH_RUN_CONCURRENCY=2
EXPOSE 8000
CMD ["uvicorn", "dvah.webapi.app:app", "--host", "0.0.0.0", "--port", "8000"]
