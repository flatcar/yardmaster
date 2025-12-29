from __future__ import annotations

import logging
from urllib.parse import quote_plus

import requests

from yardmaster.core.version import STREAM_TO_CHANNEL
from yardmaster.utils.http import HttpClient

logger = logging.getLogger("yardmaster")


class JenkinsService:
    def __init__(
        self,
        url: str,
        username: str | None,
        token: str | None,
        jobs: dict[str, str] | None = None,
        pipeline_branch: str | None = None,
        timeout: int = 30,
        retries: int = 3,
        verify_ssl: bool = True,
        http: HttpClient | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.username = username
        self.token = token
        self.jobs = jobs or {}
        self.pipeline_branch = pipeline_branch
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.http = http or HttpClient(timeout=timeout, retries=retries, verify_ssl=verify_ssl)

    def trigger_release(
        self, channel: str, version: str, dry_run: bool = False, force: bool = False
    ) -> None:
        release_version = f"{channel}-{version}"
        self.trigger_packages_all_arches(
            release_version,
            release_version,
            dry_run=dry_run,
            action=f"release {channel}:{version} (force={force})",
        )

    def trigger_packages_all_arches(
        self,
        version: str,
        scripts_ref: str,
        *,
        dry_run: bool = False,
        action: str = "packages_all_arches",
    ) -> bool:
        job_path = self._resolve_job("packages_all_arches", fallback_keys=("packages",))
        params = {
            "version": version,
            "scripts_ref": scripts_ref,
            "test_formats_amd64": "",
            "test_formats_arm64": "",
        }
        if self.pipeline_branch:
            params["PIPELINE_BRANCH"] = self.pipeline_branch
        return self._trigger_job(job_path, params, dry_run=dry_run, action=action)

    def trigger_sdk_build(
        self,
        version: str,
        scripts_ref: str,
        seed_version: str,
        *,
        dry_run: bool = False,
        action: str = "sdk",
    ) -> bool:
        job_path = self._resolve_job("sdk")
        params = {
            "version": version,
            "scripts_ref": scripts_ref,
            "seed_version": seed_version,
            "test_formats_amd64": "",
            "test_formats_arm64": "",
            "Architecture": "amd64",
        }
        if self.pipeline_branch:
            params["PIPELINE_BRANCH"] = self.pipeline_branch
        return self._trigger_job(job_path, params, dry_run=dry_run, action=action)

    def trigger_pr_build(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        job: str | None = None,
        github_token: str | None = None,
        dry_run: bool = False,
    ) -> bool:
        job_path = self._resolve_job(job or "release")
        source_branch, target_branch = self._get_pr_branches(owner, repo, pr_number, github_token)
        flatcar_version = self._get_flatcar_version(target_branch, github_token)
        release_version = self._build_pr_version(flatcar_version, source_branch)
        return self._trigger_job(
            job_path,
            {"version": release_version, "scripts_ref": source_branch},
            dry_run=dry_run,
            action=f"PR #{pr_number}",
        )

    def _get_pr_branches(
        self, owner: str, repo: str, pr_number: int, token: str | None
    ) -> tuple[str, str]:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        payload = self.http.get_json(url, headers=self._github_headers(token))
        try:
            return payload["head"]["ref"], payload["base"]["ref"]
        except KeyError as exc:
            raise RuntimeError("GitHub PR payload missing branch refs.") from exc

    def _get_flatcar_version(self, branch: str, token: str | None) -> str:
        path = "sdk_container/.repo/manifests/version.txt"
        url = f"https://api.github.com/repos/flatcar/scripts/contents/{path}?ref={branch}"
        headers = self._github_headers(token)
        headers["Accept"] = "application/vnd.github.v3.raw"
        content = self.http.get_text(url, headers=headers)
        for line in content.splitlines():
            if line.startswith("FLATCAR_VERSION_ID="):
                return line.split("=", 1)[1].strip()
        raise RuntimeError("FLATCAR_VERSION_ID not found in version.txt")

    @staticmethod
    def _build_pr_version(version: str, source_branch: str) -> str:
        parts = version.split(".")
        if len(parts) != 3:
            raise RuntimeError(f"Unexpected Flatcar version format: {version}")
        major, minor, _patch = parts
        stream = int(minor)
        if source_branch.endswith("main"):
            channel = "main"
        elif stream in STREAM_TO_CHANNEL:
            channel = STREAM_TO_CHANNEL[stream].value
        else:
            raise RuntimeError(f"Unknown stream {stream} for PR version derivation")
        return f"{channel}-{major}.{minor}.101-{source_branch}"

    def _trigger_job(
        self, job_path: str, parameters: dict[str, str], dry_run: bool, action: str
    ) -> bool:
        job_url = self._build_job_url(job_path)
        if dry_run:
            logger.info("[dry-run] Trigger Jenkins %s at %s params=%s", action, job_url, parameters)
            return True
        if not self.username or not self.token:
            raise RuntimeError(
                "Missing Jenkins credentials. Set jenkins.username and jenkins.token."
            )
        try:
            resp = requests.post(
                job_url,
                auth=(self.username, self.token),
                params=parameters,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to trigger Jenkins job: {exc}") from exc
        if resp.status_code not in {200, 201}:
            raise RuntimeError(f"Unexpected Jenkins response: {resp.status_code}")
        logger.info("Triggered Jenkins %s. Queue: %s", action, resp.headers.get("Location"))
        return True

    def _resolve_job(self, job: str, fallback_keys: tuple[str, ...] = ()) -> str:
        if job in self.jobs:
            return self.jobs[job]
        for key in fallback_keys:
            if key in self.jobs:
                return self.jobs[key]
        return job

    def _build_job_url(self, job_path: str) -> str:
        parts = [p for p in job_path.strip("/").split("/") if p]
        if not parts:
            raise RuntimeError("Jenkins job path is empty.")
        job_bits = "/".join(f"job/{quote_plus(part)}" for part in parts)
        return f"{self.url}/{job_bits}/buildWithParameters"

    @staticmethod
    def _github_headers(token: str | None) -> dict[str, str]:
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
