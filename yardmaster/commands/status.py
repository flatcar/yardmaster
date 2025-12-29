from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from tabulate import tabulate

from yardmaster.config import load_config
from yardmaster.core.version import Channel, Version
from yardmaster.services.sdk import SDKService
from yardmaster.utils.http import HttpClient

console = Console()
STATE_PATH = Path(".yardmaster/release.json")


@click.command(help="Show channel status.")
@click.argument("channels", nargs=-1, required=False)
@click.option("--show-sdk", is_flag=True, help="Show SDK versions (heuristic)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "-c", "--config", type=click.Path(exists=True, path_type=Path), default=".yardmaster.yaml"
)
def status_command(channels: list[str], show_sdk: bool, as_json: bool, config: Path) -> None:
    cfg = load_config(config)

    selected = [Channel(c) for c in channels] if channels else [Channel(k) for k in cfg.channels]
    planned_versions: dict[str, str] = {}
    release_status = ""
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            versions = state.get("versions")
            if isinstance(versions, dict):
                planned_versions = {k: str(v) for k, v in versions.items()}
            release_status = state.get("status", "")
        except json.JSONDecodeError:
            pass  # corrupt state file — proceed without planned versions

    http = HttpClient(
        timeout=cfg.network.timeout,
        retries=cfg.network.retries,
        verify_ssl=cfg.network.verify_ssl,
    )
    release_urls = {k: v.release_url for k, v in cfg.channels.items()}
    sdk = SDKService(
        http=http,
        release_urls=release_urls,
        scripts_path=cfg.paths.scripts,
        fallback_strategy=cfg.sdk.fallback_strategy,
        seed_sdk_offset=cfg.sdk.seed_sdk_offset,
    )

    rows = []
    json_payload = []
    for ch in selected:
        channel_config = cfg.channels[ch.value]
        planned_version = planned_versions.get(ch.value, "")
        planned_sdk = ""
        if planned_version:
            try:
                planned_sdk = sdk.resolve_sdk_for_release(
                    ch, Version.parse(planned_version)
                ).sdk_version
            except RuntimeError:
                planned_sdk = "unavailable"
        entry = {
            "channel": ch.value,
            "release_url": channel_config.release_url,
            "description": channel_config.description,
            "planned_release": planned_version,
            "planned_sdk": planned_sdk,
        }
        if show_sdk:
            entry["sdk"] = sdk.detect_current_sdk(ch) or ""
        json_payload.append(entry)
        rows.append(
            [
                entry["channel"],
                entry["release_url"],
                entry.get("sdk", ""),
                entry["planned_release"],
                entry["planned_sdk"],
                entry["description"],
            ]
        )

    if as_json:
        for entry in json_payload:
            entry["release_status"] = release_status
        console.print(json.dumps(json_payload, indent=2))
        return

    if release_status:
        console.print(f"Release status: [bold]{release_status}[/bold]\n")

    console.print(
        tabulate(
            rows,
            headers=[
                "Channel",
                "Release URL",
                "SDK",
                "Planned Release",
                "Planned SDK",
                "Description",
            ],
            tablefmt="github",
        )
    )
