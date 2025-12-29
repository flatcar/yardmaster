from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import click
from rich.console import Console

from yardmaster.config import Config, load_config
from yardmaster.core.release import ReleaseManager, ReleaseSpec
from yardmaster.core.version import Version
from yardmaster.services.git import GitService
from yardmaster.utils.http import HttpClient

console = Console()
STATE_PATH = Path(".yardmaster/release.json")
ISSUE_TITLE_RE = re.compile(r"\b(alpha|beta|stable|lts)\s+(\d+\.\d+\.\d+)\b", re.IGNORECASE)
EPOCH_BASE_DATE = date(2013, 7, 1)

CHANNEL_ORDER = ["alpha", "beta", "stable", "lts"]


def _parse_issue_url(issue_url: str) -> tuple[str, str, str]:
    parsed = urlparse(issue_url)
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise click.ClickException("Only github.com issue URLs are supported.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 4 or parts[2] != "issues":
        raise click.ClickException(
            "Expected GitHub issue URL like https://github.com/org/repo/issues/1234"
        )
    return parts[0], parts[1], parts[3]


def _extract_versions_from_title(title: str) -> dict[str, str]:
    matches = ISSUE_TITLE_RE.findall(title)
    if not matches:
        raise click.ClickException("Could not find channel versions in issue title.")
    versions: dict[str, str] = {}
    for channel, version in matches:
        key = channel.lower()
        if key in versions and versions[key] != version:
            raise click.ClickException(f"Conflicting versions for {key} in issue title.")
        versions[key] = version
    return versions


def _load_release_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        raise click.ClickException(f"Release state not found: {STATE_PATH}")
    state: dict[str, Any] = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return state


def _save_release_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _update_release_state(status: str) -> None:
    state = _load_release_state()
    state["status"] = status
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_release_state(state)


def _issue_api_url(issue_url: str) -> tuple[str, str]:
    owner, repo, issue_id = _parse_issue_url(issue_url)
    return issue_id, f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_id}"


def _build_http_client(cfg: Config) -> HttpClient:
    return HttpClient(
        timeout=cfg.network.timeout,
        retries=cfg.network.retries,
        verify_ssl=cfg.network.verify_ssl,
    )


def _fetch_issue_title(http: HttpClient, issue_url: str) -> str:
    issue_id, api_url = _issue_api_url(issue_url)
    title: str | None = http.get_json(api_url).get("title")
    if not title:
        raise click.ClickException(f"Missing issue title for {issue_id}.")
    return title


def _specs_from_state(state: dict[str, Any], http: HttpClient, skip_issue_check: bool) -> list[str]:
    versions = state.get("versions")
    if not isinstance(versions, dict) or not versions:
        raise click.ClickException("Release state has no versions.")

    issue_url = state.get("issue_url")
    if issue_url and not skip_issue_check:
        try:
            title = _fetch_issue_title(http, issue_url)
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(
                "Could not refresh issue title. Use --skip-issue-check or pass specs explicitly."
            ) from exc
        if _extract_versions_from_title(title) != versions:
            raise click.ClickException(
                "Release state is out of date with the issue title. Run `yardmaster release init --force <issue-url>`."
            )

    return [f"{ch}:{versions[ch]}" for ch in CHANNEL_ORDER if ch in versions]


def _expected_epoch_today() -> int:
    return (date.today() - EPOCH_BASE_DATE).days


def _reconcile_alpha_epoch(specs: list[ReleaseSpec], verbose: bool) -> list[ReleaseSpec]:
    expected_epoch = _expected_epoch_today()
    updated: list[ReleaseSpec] = []
    for spec in specs:
        if spec.channel.value != "alpha" or spec.version.stream != 0 or spec.version.revision != 0:
            if spec.channel.value == "alpha" and spec.version.stream != 0 and verbose:
                console.print("[yellow]Alpha stream is not 0; skipping epoch check.[/yellow]")
            updated.append(spec)
            continue
        if spec.version.epoch == expected_epoch:
            updated.append(spec)
            continue

        provided_version = f"{spec.version.epoch}.{spec.version.stream}.{spec.version.revision}"
        expected_version = f"{expected_epoch}.{spec.version.stream}.{spec.version.revision}"
        prompt = (
            f"Alpha epoch {spec.version.epoch} does not match expected {expected_epoch} "
            f"(days since {EPOCH_BASE_DATE}).\n"
            f"Provided:\n  1. {provided_version}\n"
            f"Expected:\n  2. {expected_version}\n"
            "Choose version (1 or 2)"
        )
        choice = click.prompt(prompt, type=click.IntRange(1, 2), default=2, prompt_suffix=": ")
        chosen_version = expected_version if choice == 2 else provided_version
        console.print(f"[cyan]Proceeding with alpha version {chosen_version}[/cyan]")
        if choice == 2:
            updated.append(
                ReleaseSpec(
                    channel=spec.channel,
                    version=Version(expected_epoch, spec.version.stream, spec.version.revision),
                )
            )
        else:
            updated.append(spec)
    return updated


def _run_release(
    specs: list[str],
    *,
    phase: str,
    dry_run: bool,
    force: bool,
    skip_jenkins: bool,
    skip_issue_check: bool,
    config: Path,
    verbose: bool,
) -> None:
    cfg = load_config(config)
    if not specs:
        if verbose:
            console.print(f"[cyan]Using stored release state from {STATE_PATH}[/cyan]")
        http = _build_http_client(cfg)
        specs = _specs_from_state(_load_release_state(), http, skip_issue_check)

    manager = ReleaseManager(cfg, dry_run=dry_run, verbose=verbose)
    parsed = _reconcile_alpha_epoch(manager.parse_specs(specs), verbose)
    manager.run(parsed, phase=phase, force=force, skip_jenkins=skip_jenkins)


@click.group(
    help="Release one or more channels: CHANNEL:VERSION ...",
    invoke_without_command=True,
    context_settings={"allow_extra_args": True},
)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--force", is_flag=True, help="Force tag creation even if exists")
@click.option("--skip-jenkins", is_flag=True, help="Skip Jenkins build trigger")
@click.option(
    "--skip-issue-check", is_flag=True, help="Skip verifying issue title when using release state"
)
@click.option(
    "-c", "--config", type=click.Path(exists=True, path_type=Path), default=".yardmaster.yaml"
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def release_command(
    ctx: click.Context,
    dry_run: bool,
    force: bool,
    skip_jenkins: bool,
    skip_issue_check: bool,
    config: Path,
    verbose: bool,
) -> None:
    if ctx.invoked_subcommand is not None:
        ctx.obj = {"config": config, "verbose": verbose}
        return

    _run_release(
        list(ctx.args),
        phase="all",
        dry_run=dry_run,
        force=force,
        skip_jenkins=skip_jenkins,
        skip_issue_check=skip_issue_check,
        config=config,
        verbose=verbose,
    )


@release_command.command("run", help="Run release steps for a phase.")
@click.argument("specs", nargs=-1, required=False)
@click.option("--pre", "phase_pre", is_flag=True, help="Run pre-release steps")
@click.option("--post", "phase_post", is_flag=True, help="Run post-release steps")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--force", is_flag=True, help="Force tag creation even if exists")
@click.option("--skip-jenkins", is_flag=True, help="Skip Jenkins build trigger")
@click.option(
    "--skip-issue-check", is_flag=True, help="Skip verifying issue title when using release state"
)
@click.option(
    "-c", "--config", type=click.Path(exists=True, path_type=Path), default=".yardmaster.yaml"
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def release_run(
    specs: list[str],
    phase_pre: bool,
    phase_post: bool,
    dry_run: bool,
    force: bool,
    skip_jenkins: bool,
    skip_issue_check: bool,
    config: Path,
    verbose: bool,
) -> None:
    if phase_pre == phase_post:
        raise click.ClickException("Choose exactly one of --pre or --post.")
    phase = "pre" if phase_pre else "post"
    if phase == "post":
        state = _load_release_state()
        if state.get("status") != "in_progress":
            raise click.ClickException(
                "Post-release steps require a completed pre-release run. Run `yardmaster release run --pre` first."
            )
    _run_release(
        list(specs),
        phase=phase,
        dry_run=dry_run,
        force=force,
        skip_jenkins=skip_jenkins,
        skip_issue_check=skip_issue_check,
        config=config,
        verbose=verbose,
    )
    if not dry_run:
        if phase == "pre":
            _update_release_state("in_progress")
        elif phase == "post":
            _update_release_state("completed")


@release_command.command("complete", help="Mark the current release as completed.")
def release_complete() -> None:
    state = _load_release_state()
    status = state.get("status")
    if status == "completed":
        console.print("[yellow]Release is already marked as completed.[/yellow]")
        return
    _update_release_state("completed")
    console.print("[green]✓[/green] Release marked as completed.")


@release_command.command("init", help="Initialize release state from a GitHub issue.")
@click.argument("issue_url", required=True)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without writing state or git changes"
)
@click.option("--force", is_flag=True, help="Overwrite existing release state and tag")
@click.option("--no-push", is_flag=True, help="Do not push commit/tag to origin")
@click.pass_context
def release_init(
    ctx: click.Context, issue_url: str, dry_run: bool, force: bool, no_push: bool
) -> None:
    cfg_path = Path(".yardmaster.yaml")
    verbose = False
    if ctx.obj:
        cfg_path = ctx.obj.get("config", cfg_path)
        verbose = ctx.obj.get("verbose", False)

    cfg = load_config(cfg_path)
    http = _build_http_client(cfg)
    if verbose:
        console.print(f"[cyan]Fetching issue metadata from {issue_url}[/cyan]")
    issue_id, _api_url = _issue_api_url(issue_url)
    title = _fetch_issue_title(http, issue_url)
    versions = _extract_versions_from_title(title)
    if verbose:
        console.print(f"[cyan]Parsed versions from issue title: {versions}[/cyan]")

    tag_name = f"release-{issue_id}"
    git = GitService()
    git.ensure_repo()
    tag_already_exists = git.tag_exists(tag_name)
    existing_state = _load_release_state() if STATE_PATH.exists() else None
    if existing_state and not force:
        if (
            existing_state.get("issue_url") != issue_url
            or existing_state.get("versions") != versions
        ):
            raise click.ClickException(
                f"Release state already exists and differs from issue {issue_id}. Use --force to overwrite."
            )
        if tag_already_exists and verbose:
            console.print(f"[cyan]Existing tag {tag_name} found; reusing it.[/cyan]")

    now = datetime.now(timezone.utc).isoformat()
    state = {
        "issue_url": issue_url,
        "issue_title": title,
        "issue_id": issue_id,
        "versions": versions,
        "status": "planned",
        "created_at": now,
        "updated_at": now,
    }
    if dry_run:
        console.print("[cyan]Dry-run[/cyan]: release init will perform the following actions:")
        console.print(f"  • Write state to {STATE_PATH}")
        console.print(f"  • Commit {STATE_PATH}")
        console.print(f"  • Tag {tag_name}")
        if no_push:
            console.print("  • Skip pushing to origin (--no-push)")
        else:
            console.print("  • Push commit and tag to origin")
        if verbose:
            console.print(f"[cyan]Computed state[/cyan]: {state}")
        return
    if verbose:
        console.print(f"[cyan]Writing release state to {STATE_PATH}[/cyan]")
    _save_release_state(state)

    if git.paths_changed([STATE_PATH]):
        if verbose:
            console.print("[cyan]Committing release state[/cyan]")
        git.add_paths([STATE_PATH])
        git.commit_paths([STATE_PATH], f"chore: init release state for issue {issue_id}")
    else:
        console.print("[yellow]Release state unchanged; skipping commit.[/yellow]")
    if verbose:
        console.print(f"[cyan]Creating tag {tag_name}[/cyan]")
    if tag_already_exists and not force:
        if verbose:
            console.print(f"[cyan]Tag {tag_name} already exists; skipping creation.[/cyan]")
    else:
        git.create_tag(tag_name, f"Yardmaster release init for {issue_url}", force=force)

    if no_push:
        console.print("[yellow]Skipped pushing release state and tag.[/yellow]")
        return

    try:
        git.get_remote_url("origin")
    except RuntimeError as exc:
        raise click.ClickException("Git remote 'origin' not found; cannot push.") from exc

    if verbose:
        console.print("[cyan]Pushing commit to origin[/cyan]")
    git.push_ref("origin", "HEAD")
    if verbose:
        console.print(f"[cyan]Pushing tag {tag_name} to origin[/cyan]")
    git.push_ref("origin", tag_name)
    if verbose:
        console.print(f"[green]Pushed release state and tag {tag_name} to origin.[/green]")
