from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from yardmaster import __version__
from yardmaster.commands.jenkins import jenkins_command
from yardmaster.commands.release import release_command
from yardmaster.commands.retag import retag_command
from yardmaster.commands.sdk import sdk_command
from yardmaster.commands.status import status_command
from yardmaster.config import load_config
from yardmaster.utils.logger import setup_logger

console = Console()
CONFIG_FILE = ".yardmaster.yaml"
CONFIG_ENV_VAR = "YARDMASTER_CONFIG"


@click.group()
@click.version_option(version=__version__, prog_name="yardmaster")
@click.option(
    "-c",
    "--config",
    type=click.Path(path_type=Path),
    default=None,
    envvar=CONFIG_ENV_VAR,
    help=f"Configuration file path (env: {CONFIG_ENV_VAR})",
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx: click.Context, config: Path | None, verbose: bool) -> None:
    """🚂 Yardmaster - Flatcar Container Linux Release Management Tool"""
    ctx.ensure_object(dict)

    if config is None:
        config = Path(CONFIG_FILE)

    if not config.exists():
        console.print(f"[red]Error: Config file not found: {config}[/red]")
        console.print(
            "Copy [cyan].yardmaster.yaml.sample[/cyan] to "
            f"[cyan]{CONFIG_FILE}[/cyan] and update the values."
        )
        sys.exit(1)

    ctx.obj["config"] = load_config(config)
    ctx.obj["verbose"] = verbose
    log_level = "DEBUG" if verbose else ctx.obj["config"].logging.level
    setup_logger(log_level, fmt=ctx.obj["config"].logging.format)


cli.add_command(release_command, name="release")
cli.add_command(jenkins_command, name="jenkins")
cli.add_command(retag_command, name="retag")
cli.add_command(sdk_command, name="sdk")
cli.add_command(status_command, name="status")


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
