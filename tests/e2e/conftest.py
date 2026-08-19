"""E2E fixtures: run the real FastAPI services on background uvicorn threads.

These tests are marked ``e2e`` and excluded from CI by the default ``-m 'not e2e'``.
Run them manually with ``uv run pytest -m e2e``.
"""

from __future__ import annotations

import threading
import time

import httpx
import pytest
import uvicorn

from services.cloud.app import app as cloud_app
from services.email.app import app as email_app
from services.files.app import app as files_app
from services.github.app import app as github_app

_PORTS = {"files": 8001, "github": 8002, "email": 8003, "cloud": 8004}
_APPS = {"files": files_app, "github": github_app, "email": email_app, "cloud": cloud_app}
BASE_URLS = {name: f"http://127.0.0.1:{port}" for name, port in _PORTS.items()}


class _Server(uvicorn.Server):
    def install_signal_handlers(self) -> None:  # threads can't set signal handlers
        pass


def _wait_healthy(base_url: str, attempts: int = 100) -> None:
    for _ in range(attempts):
        try:
            if httpx.get(f"{base_url}/_health", timeout=0.5).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.05)
    raise RuntimeError(f"service at {base_url} never became healthy")


@pytest.fixture(scope="session")
def services():
    servers: list[_Server] = []
    threads: list[threading.Thread] = []
    for name, app in _APPS.items():
        config = uvicorn.Config(app, host="127.0.0.1", port=_PORTS[name], log_level="warning")
        server = _Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)
    for base_url in BASE_URLS.values():
        _wait_healthy(base_url)
    yield BASE_URLS
    for server in servers:
        server.should_exit = True
    for thread in threads:
        thread.join(timeout=5)


@pytest.fixture
def reset_services(services):
    """Reset every service to a known seed before each test."""
    def _reset(seeds: dict | None = None) -> None:
        seeds = seeds or {}
        for name, base_url in services.items():
            httpx.post(f"{base_url}/_reset", json=seeds.get(name, {}), timeout=2.0)
    _reset()
    return _reset
