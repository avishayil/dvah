"""In-memory backends for the simulated services.

Each store is seedable and resettable so tests are deterministic. These are the
"external systems" whose state exploits try to corrupt (e.g. deleting a prod DB).
"""

from __future__ import annotations


class FileStore:
    """A tiny simulated filesystem: path -> contents."""

    def __init__(self, seed: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = dict(seed or {})

    def reset(self, seed: dict[str, str] | None = None) -> None:
        self._files = dict(seed or {})

    def exists(self, path: str) -> bool:
        return path in self._files

    def read(self, path: str) -> str:
        return self._files[path]

    def delete(self, path: str) -> bool:
        existed = path in self._files
        self._files.pop(path, None)
        return existed

    def rename(self, path: str, dest: str) -> bool:
        if path not in self._files:
            return False
        self._files[dest] = self._files.pop(path)
        return True


class GithubStore:
    """A tiny simulated GitHub: repo -> {"issues": [...], "exists": bool}."""

    def __init__(self, seed: dict[str, dict] | None = None) -> None:
        self._repos: dict[str, dict] = dict(seed or {})

    def reset(self, seed: dict[str, dict] | None = None) -> None:
        self._repos = dict(seed or {})

    def exists(self, repo: str) -> bool:
        return repo in self._repos

    def list_issues(self, repo: str) -> list[dict]:
        return list(self._repos.get(repo, {}).get("issues", []))

    def comment(self, repo: str, issue: int, body: str) -> bool:
        return self.exists(repo)

    def delete_repository(self, repo: str) -> bool:
        existed = repo in self._repos
        self._repos.pop(repo, None)
        return existed
