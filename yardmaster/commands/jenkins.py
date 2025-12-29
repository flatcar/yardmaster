from __future__ import annotations

import os

import click
from rich.console import Console

from yardmaster.services.jenkins import JenkinsService

console = Console()


@click.group(help="Jenkins utilities.")
def jenkins_command() -> None:
    pass


@jenkins_command.command("pr-build", help="Trigger a Jenkins build for a GitHub PR (kernel tests).")
@click.argument("owner")
@click.argument("repo")
@click.argument("pr", type=int)
@click.option("--job", default="release", help="Jenkins job key or path")
@click.option("--github-token", default=None, help="GitHub token (or set GITHUB_TOKEN)")
@click.option("--dry-run", is_flag=True, help="Show what would be sent without triggering")
@click.pass_context
def jenkins_pr_build(
    ctx: click.Context,
    owner: str,
    repo: str,
    pr: int,
    job: str,
    github_token: str | None,
    dry_run: bool,
) -> None:
    cfg = ctx.obj["config"]
    jenkins = JenkinsService(
        url=cfg.jenkins.url,
        username=cfg.jenkins.username,
        token=cfg.jenkins.token,
        jobs=cfg.jenkins.jobs,
        pipeline_branch=cfg.jenkins.pipeline_branch,
        timeout=cfg.network.timeout,
        retries=cfg.network.retries,
        verify_ssl=cfg.network.verify_ssl,
    )
    try:
        ok = jenkins.trigger_pr_build(
            owner=owner,
            repo=repo,
            pr_number=pr,
            job=job,
            github_token=github_token or os.getenv("GITHUB_TOKEN"),
            dry_run=dry_run,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    if ok:
        console.print("[green]✓[/green] Jenkins build triggered.")
