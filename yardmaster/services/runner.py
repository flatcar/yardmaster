from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("yardmaster")


class CommandRunner:
    def run(
        self,
        args: list[str],
        *,
        dry_run: bool = False,
        env: dict[str, str] | None = None,
        display_env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        env_prefix = ""
        if display_env:
            env_prefix = " ".join(f"{k}={v}" for k, v in display_env.items()) + " "
        msg = f"{env_prefix}{' '.join(args)}"
        if dry_run:
            logger.info("[dry-run] %s", msg)
            return
        logger.info("[run] %s", msg)
        subprocess.run(args, check=True, capture_output=True, text=True, env=env, cwd=cwd)

    def run_mirror_repos_branch(
        self,
        script_path: Path,
        base_branch: str,
        branch_name: str,
        *,
        dry_run: bool = False,
    ) -> None:
        if not script_path.exists():
            raise RuntimeError(f"mirror-repos-branch not found at {script_path}")
        self.run(
            [str(script_path), base_branch, branch_name],
            dry_run=dry_run,
            cwd=script_path.parent,
        )

    def run_tag_release(
        self,
        script_path: Path,
        *,
        channel: str,
        version: str,
        sdk_version: str,
        dry_run: bool = False,
    ) -> None:
        if not script_path.exists():
            raise RuntimeError(f"tag-release not found at {script_path}")
        env_overrides = {"VERSION": version, "SDK_VERSION": sdk_version, "CHANNEL": channel}
        merged_env = {**os.environ, **env_overrides}
        self.run(
            [str(script_path)],
            dry_run=dry_run,
            env=merged_env,
            display_env=env_overrides,
            cwd=script_path.parent,
        )
