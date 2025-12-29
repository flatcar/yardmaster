from __future__ import annotations

import logging
import subprocess
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger("yardmaster")


class GitService:
    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        logger.debug("git %s", " ".join(args))
        result = subprocess.run(["git", *args], capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.error("git %s failed: %s", " ".join(args), stderr)
            raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
        return result

    def ensure_repo(self) -> None:
        try:
            self._run(["rev-parse", "--is-inside-work-tree"])
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Not a git repository.") from exc

    def list_tags(self, repo_path: Path) -> list[str]:
        if not repo_path.exists():
            raise RuntimeError(f"Repository path not found: {repo_path}")
        result = self._run(["-C", str(repo_path), "tag", "--list"])
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def fetch_tags(self, repo_path: Path) -> None:
        if not repo_path.exists():
            raise RuntimeError(f"Repository path not found: {repo_path}")
        self._run(["-C", str(repo_path), "fetch", "--tags", "--force"])

    def tag_exists(self, tag: str) -> bool:
        try:
            self._run(["rev-parse", "--verify", f"refs/tags/{tag}"])
        except subprocess.CalledProcessError:
            return False
        return True

    def add_paths(self, paths: Iterable[Path]) -> None:
        self.ensure_repo()
        self._run(["add", "--", *[str(p) for p in paths]])

    def commit_paths(self, paths: Iterable[Path], message: str) -> None:
        self.ensure_repo()
        self._run(["commit", "-m", message, "--", *[str(p) for p in paths]])

    def paths_changed(self, paths: Iterable[Path]) -> bool:
        self.ensure_repo()
        result = self._run(["status", "--porcelain", "--", *[str(p) for p in paths]])
        return bool(result.stdout.strip())

    def create_tag(self, tag: str, message: str, force: bool = False) -> None:
        self.ensure_repo()
        args = ["tag", "-a"]
        if force:
            args.append("-f")
        args.extend([tag, "-m", message])
        self._run(args)

    def get_remote_url(self, remote: str) -> str:
        self.ensure_repo()
        return self._run(["remote", "get-url", remote]).stdout.strip()

    def push_ref(self, remote: str, ref: str) -> None:
        self.ensure_repo()
        self._run(["push", remote, ref])
