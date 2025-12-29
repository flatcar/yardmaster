from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

from yardmaster.config import load_config
from yardmaster.core.version import Channel, Version
from yardmaster.services.runner import CommandRunner
from yardmaster.services.sdk import SDKService
from yardmaster.utils.http import HttpClient

console = Console()
STATE_PATH = Path(".yardmaster/release.json")


@click.command(help="Retag the ongoing release for a channel.")
@click.argument("channel", nargs=1, required=True)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--force", is_flag=True, help="Force retag (delete existing tag)")
@click.option(
    "-c", "--config", type=click.Path(exists=True, path_type=Path), default=".yardmaster.yaml"
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def retag_command(
    channel: str,
    dry_run: bool,
    force: bool,
    config: Path,
    verbose: bool,
) -> None:
    _ = force
    cfg = load_config(config)
    ch = Channel(channel)
    if not STATE_PATH.exists():
        raise click.ClickException(f"Release state not found: {STATE_PATH}")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    versions = state.get("versions")
    if not isinstance(versions, dict) or ch.value not in versions:
        raise click.ClickException(f"No ongoing release for channel {ch.value}.")
    version = Version.parse(str(versions[ch.value]))

    if not click.confirm(f"Retag ongoing {ch.value}:{version}?", default=False):
        console.print("[yellow]Cancelled.[/yellow]")
        return

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
    resolution = sdk.resolve_sdk_for_release(ch, version)
    if verbose:
        console.print(f"[cyan]SDK[/cyan]: {ch.value}:{version} -> {resolution.sdk_version}")

    script_path = Path(cfg.paths.build_scripts) / "tag-release"
    CommandRunner().run_tag_release(
        script_path,
        channel=ch.value,
        version=str(version),
        sdk_version=resolution.sdk_version,
        dry_run=dry_run,
    )
