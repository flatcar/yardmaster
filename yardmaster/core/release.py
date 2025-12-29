from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.console import Console

from yardmaster.config import Config
from yardmaster.core.validator import ReleaseValidator
from yardmaster.core.version import Channel, Version
from yardmaster.services.git import GitService
from yardmaster.services.jenkins import JenkinsService
from yardmaster.services.runner import CommandRunner
from yardmaster.services.sdk import SDKService
from yardmaster.utils.http import HttpClient

console = Console()


@dataclass(frozen=True, slots=True)
class ReleaseSpec:
    channel: Channel
    version: Version


@dataclass(frozen=True, slots=True)
class ReleaseStep:
    phase: str
    name: str
    action: Callable[[ReleaseManager, Sequence[ReleaseSpec], bool, bool], None]


class ReleaseManager:
    def __init__(self, config: Config, dry_run: bool = False, verbose: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run
        self.verbose = verbose

        self.validator = ReleaseValidator()
        self.git = GitService()
        self.jenkins = JenkinsService(
            url=config.jenkins.url,
            username=config.jenkins.username,
            token=config.jenkins.token,
            jobs=config.jenkins.jobs,
            pipeline_branch=config.jenkins.pipeline_branch,
            timeout=config.network.timeout,
            retries=config.network.retries,
            verify_ssl=config.network.verify_ssl,
        )
        http = HttpClient(
            timeout=config.network.timeout,
            retries=config.network.retries,
            verify_ssl=config.network.verify_ssl,
        )
        release_urls = {k: v.release_url for k, v in config.channels.items()}
        self.sdk = SDKService(
            http=http,
            release_urls=release_urls,
            scripts_path=config.paths.scripts,
            fallback_strategy=config.sdk.fallback_strategy,
            seed_sdk_offset=config.sdk.seed_sdk_offset,
        )
        self.runner = CommandRunner()
        self.steps = self._build_steps()
        self.steps_by_phase = self._index_steps(self.steps)

    def _build_steps(self) -> list[ReleaseStep]:
        return [
            ReleaseStep(
                "pre", "prepare_release_branch", ReleaseManager._step_prepare_release_branch
            ),
            ReleaseStep("pre", "tag_release", ReleaseManager._step_tag_release),
            ReleaseStep("pre", "trigger_jenkins", ReleaseManager._step_trigger_jenkins),
        ]

    @staticmethod
    def _index_steps(steps: Sequence[ReleaseStep]) -> dict[str, list[ReleaseStep]]:
        grouped: dict[str, list[ReleaseStep]] = {}
        for step in steps:
            grouped.setdefault(step.phase, []).append(step)
        return grouped

    @staticmethod
    def parse_specs(values: Sequence[str]) -> list[ReleaseSpec]:
        specs: list[ReleaseSpec] = []
        for v in values:
            if ":" not in v:
                raise ValueError(f"Invalid spec '{v}'. Expected CHANNEL:VERSION.")
            ch_s, ver_s = v.split(":", 1)
            specs.append(
                ReleaseSpec(channel=Channel(ch_s.strip()), version=Version.parse(ver_s.strip()))
            )
        return specs

    def validate(self, specs: Sequence[ReleaseSpec]) -> None:
        if self.config.validation.require_unique_channels:
            if self.verbose:
                console.print("[cyan]Validating unique channels[/cyan]")
            res = self.validator.validate_unique_channels(specs)
            if not res.ok:
                for e in res.errors:
                    console.print(f"[red]Error:[/red] {e}")
                raise RuntimeError("Validation failed")
            for w in res.warnings:
                console.print(f"[yellow]Warning:[/yellow] {w}")

        if self.config.validation.check_version_progression:
            if self.verbose:
                console.print("[cyan]Validating version progression[/cyan]")
            res = self.validator.validate_version_progression(specs)
            for w in res.warnings:
                console.print(f"[yellow]Warning:[/yellow] {w}")

    def run(
        self,
        specs: Sequence[ReleaseSpec],
        phase: str,
        force: bool = False,
        skip_jenkins: bool = False,
    ) -> None:
        self.validate(specs)

        console.print("[bold]Yardmaster[/bold] preparing release:")
        for s in specs:
            console.print(f"  • {s.channel.value}: {s.version}")

        if self.dry_run:
            console.print("[cyan]Dry-run[/cyan]: no changes will be made.")

        phases = ["pre", "post"] if phase == "all" else [phase]
        for current_phase in phases:
            self._run_steps(current_phase, specs, force=force, skip_jenkins=skip_jenkins)

        console.print("[green]✓[/green] Done.")

    def release(
        self, specs: Sequence[ReleaseSpec], force: bool = False, skip_jenkins: bool = False
    ) -> None:
        self.run(specs, phase="all", force=force, skip_jenkins=skip_jenkins)

    def _run_steps(
        self, phase: str, specs: Sequence[ReleaseSpec], force: bool, skip_jenkins: bool
    ) -> None:
        phase_steps = self.steps_by_phase.get(phase, [])
        if not phase_steps:
            if self.verbose:
                console.print(f"[yellow]No {phase} steps configured.[/yellow]")
            return

        for step in phase_steps:
            if self.verbose:
                console.print(f"[cyan]Step[/cyan]: {step.name}")
            step.action(self, specs, force, skip_jenkins)

    # Alpha major releases (stream 0, revision 0) require a new branch based on
    # the epoch. Maintenance releases and non-alpha channels skip this step.
    def _step_prepare_release_branch(
        self,
        specs: Sequence[ReleaseSpec],
        _force: bool,
        _skip_jenkins: bool,
    ) -> None:
        for s in specs:
            if s.channel.value != "alpha":
                continue
            if s.version.stream != 0:
                if self.verbose:
                    console.print(
                        "[yellow]Alpha stream is not 0; skipping release branch creation.[/yellow]"
                    )
                continue
            if not s.version.is_major_release():
                continue

            branch_name = f"flatcar-{s.version.epoch}"
            script_path = Path(self.config.paths.build_scripts) / "mirror-repos-branch"
            console.print(
                f"[cyan]Prepare[/cyan]: Create Release branch for {s.channel.value} {s.version} -> {branch_name}"
            )
            self.runner.run_mirror_repos_branch(
                script_path=script_path,
                base_branch="main",
                branch_name=branch_name,
                dry_run=self.dry_run,
            )

    def _step_trigger_jenkins(
        self, specs: Sequence[ReleaseSpec], force: bool, skip_jenkins: bool
    ) -> None:
        if skip_jenkins:
            if self.verbose:
                console.print("[yellow]Skipping Jenkins triggers.[/yellow]")
            return
        if self.verbose:
            console.print("[cyan]Triggering Jenkins releases[/cyan]")
        for s in specs:
            resolution = self.sdk.resolve_sdk_for_release(s.channel, s.version)
            release_version = f"{s.channel.value}-{s.version}"
            scripts_ref = release_version
            sdk_build = resolution.sdk_version == str(s.version)
            if sdk_build:
                seed_version = self.sdk.detect_current_sdk(Channel.alpha)
                if not seed_version:
                    seed_version = self.sdk.seed_sdk_version_for(s.version)
                self.jenkins.trigger_sdk_build(
                    release_version,
                    scripts_ref,
                    seed_version,
                    dry_run=self.dry_run,
                    action=f"sdk {s.channel.value}:{s.version} (force={force})",
                )
            else:
                self.jenkins.trigger_packages_all_arches(
                    release_version,
                    scripts_ref,
                    dry_run=self.dry_run,
                    action=f"packages_all_arches {s.channel.value}:{s.version} (force={force})",
                )
            if self.verbose:
                job_name = "sdk" if sdk_build else "packages_all_arches"
                console.print(
                    f"  SDK for {s.channel.value}:{s.version} -> {resolution.sdk_version}"
                )
                console.print(f"  Jenkins job: {job_name}")

    def _step_tag_release(
        self,
        specs: Sequence[ReleaseSpec],
        _force: bool,
        _skip_jenkins: bool,
    ) -> None:
        script_path = Path(self.config.paths.build_scripts) / "tag-release"
        for s in specs:
            resolution = self.sdk.resolve_sdk_for_release(s.channel, s.version)
            console.print(
                f"[cyan]Prepare[/cyan]: Tag release for {s.channel.value} {s.version} "
                f"(SDK {resolution.sdk_version})"
            )
            self.runner.run_tag_release(
                script_path,
                channel=s.channel.value,
                version=str(s.version),
                sdk_version=resolution.sdk_version,
                dry_run=self.dry_run,
            )
