from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yardmaster.core.version import CHANNEL_TO_STREAM, STREAM_TO_CHANNEL, Channel, Version
from yardmaster.services.git import GitService
from yardmaster.utils.http import HttpClient


@dataclass(frozen=True, slots=True)
class SDKResolution:
    channel: Channel
    version: Version
    previous_channel: Channel | None
    previous_version: Version | None
    lookup_url: str | None
    sdk_version: str
    note: str = ""


class SDKService:
    def __init__(
        self,
        *,
        http: HttpClient,
        release_urls: dict[str, str],
        scripts_path: str | None,
        fallback_strategy: str = "major_version",
        seed_sdk_offset: int = 1000,
    ) -> None:
        self.http = http
        self.release_urls = release_urls
        self.scripts_path = scripts_path
        self.fallback_strategy = fallback_strategy
        self.seed_sdk_offset = seed_sdk_offset
        self.git = GitService()

    def resolve_sdk_for_release(self, channel: Channel, version: Version) -> SDKResolution:
        previous = self._previous_release(channel, version)
        if previous is None:
            return SDKResolution(
                channel=channel,
                version=version,
                previous_channel=None,
                previous_version=None,
                lookup_url=None,
                sdk_version=str(version),
                note="alpha major uses its own SDK",
            )

        prev_channel, prev_version = previous
        note = ""
        if version.revision == 0 and version.stream > 0:
            prev_version = self._latest_tag_version(prev_channel, version.epoch)
            note = "previous stream latest tag"
        url = self._version_url(prev_channel, prev_version)
        sdk_version = self._fetch_sdk_version(url)
        return SDKResolution(
            channel=channel,
            version=version,
            previous_channel=prev_channel,
            previous_version=prev_version,
            lookup_url=url,
            sdk_version=sdk_version,
            note=note,
        )

    def detect_current_sdk(self, channel: Channel) -> str | None:
        url = f"{self._release_base(channel)}/amd64-usr/current/version.txt"
        try:
            return self._fetch_sdk_version(url)
        except RuntimeError:
            return None

    def _previous_release(
        self, channel: Channel, version: Version
    ) -> tuple[Channel, Version] | None:
        if version.revision > 0:
            return channel, Version(version.epoch, version.stream, version.revision - 1)
        if version.stream == 0:
            return None
        prev_stream = version.stream - 1
        prev_channel = STREAM_TO_CHANNEL.get(prev_stream)
        if prev_channel is None:
            raise RuntimeError(f"Unsupported stream {prev_stream} for previous release.")
        return prev_channel, Version(version.epoch, prev_stream, 0)

    def _fetch_sdk_version(self, url: str) -> str:
        for line in self.http.get_text(url).splitlines():
            if line.startswith("FLATCAR_SDK_VERSION="):
                return line.split("=", 1)[1].strip()
        raise RuntimeError(f"SDK version not found in {url}")

    def _latest_tag_version(self, channel: Channel, epoch: int) -> Version:
        repo_path = self._scripts_path()
        self.git.fetch_tags(repo_path)
        prefix = f"{channel.value}-"
        candidates = []
        for tag in self.git.list_tags(repo_path):
            if not tag.startswith(prefix):
                continue
            try:
                parsed = Version.parse(tag[len(prefix) :])
            except ValueError:
                continue
            if parsed.epoch != epoch:
                continue
            if parsed.stream != CHANNEL_TO_STREAM.get(channel, parsed.stream):
                continue
            candidates.append(parsed)
        if not candidates:
            raise RuntimeError(f"No tags found for {channel.value} epoch {epoch} in scripts repo.")
        return max(candidates, key=lambda v: v.to_tuple())

    def _scripts_path(self) -> Path:
        if not self.scripts_path:
            raise RuntimeError("scripts repo path is required to resolve previous stream tags.")
        return Path(self.scripts_path).expanduser()

    def _release_base(self, channel: Channel) -> str:
        base = self.release_urls.get(channel.value, "")
        if base:
            return base.rstrip("/")
        return f"https://{channel.value}.release.flatcar-linux.net"

    def _version_url(self, channel: Channel, version: Version) -> str:
        return f"{self._release_base(channel)}/amd64-usr/{version}/version.txt"

    def fallback_sdk_version(self, version: Version) -> str:
        if self.fallback_strategy == "seed_offset":
            return f"{max(0, version.epoch - self.seed_sdk_offset)}.0.0"
        return f"{version.epoch}.0.0"

    def seed_sdk_version_for(self, version: Version) -> str:
        return f"{max(0, version.epoch - self.seed_sdk_offset)}.0.0"
