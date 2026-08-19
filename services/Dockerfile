# Shared image for all DVAH simulated services. The concrete app + port is chosen by
# the `command` in docker-compose.yml.
FROM python:3.12.3-slim
WORKDIR /app
RUN pip install --no-cache-dir \
    "fastapi>=0.111" "uvicorn>=0.30" "pydantic>=2.6" "pyyaml>=6.0" "httpx>=0.27"
COPY dvah ./dvah
COPY services ./services
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "services.files.app:app", "--host", "0.0.0.0", "--port", "8000"]
