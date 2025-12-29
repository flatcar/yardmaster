from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from tabulate import tabulate

from yardmaster.config import load_config
from yardmaster.core.release import ReleaseManager
from yardmaster.core.version import STREAM_TO_CHANNEL
from yardmaster.services.sdk import SDKService
from yardmaster.utils.http import HttpClient

console = Console()


@click.group(help="SDK utilities.")
def sdk_command() -> None:
    pass


@sdk_command.command("determine", help="Determine SDK versions for upcoming releases.")
@click.argument("specs", nargs=-1, required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option(
    "-c", "--config", type=click.Path(exists=True, path_type=Path), default=".yardmaster.yaml"
)
def sdk_determine(specs: list[str], as_json: bool, config: Path) -> None:
    cfg = load_config(config)
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

    parsed = ReleaseManager.parse_specs(list(specs))
    rows = []
    json_payload = []
    for spec in parsed:
        resolution = sdk.resolve_sdk_for_release(spec.channel, spec.version)
        expected = STREAM_TO_CHANNEL.get(spec.version.stream)
        note = resolution.note
        if expected and expected != spec.channel:
            note = f"{note} stream/channel mismatch" if note else "stream/channel mismatch"
        prev_ch = resolution.previous_channel.value if resolution.previous_channel else ""
        prev_ver = str(resolution.previous_version) if resolution.previous_version else ""
        json_payload.append(
            {
                "channel": spec.channel.value,
                "version": str(spec.version),
                "previous_channel": prev_ch,
                "previous_version": prev_ver,
                "sdk_version": resolution.sdk_version,
                "lookup_url": resolution.lookup_url or "",
                "note": note,
            }
        )
        rows.append(
            [
                spec.channel.value,
                str(spec.version),
                prev_ch,
                prev_ver,
                resolution.sdk_version,
                resolution.lookup_url or "",
                note,
            ]
        )

    if as_json:
        console.print(json.dumps(json_payload, indent=2))
        return

    console.print(
        tabulate(
            rows,
            headers=[
                "Channel",
                "Version",
                "Prev Channel",
                "Prev Version",
                "SDK",
                "Lookup URL",
                "Note",
            ],
            tablefmt="github",
        )
    )
