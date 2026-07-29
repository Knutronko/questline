"""Questline CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from questline import __version__
from questline.core.config import load_settings
from questline.core.errors import AuthoringError, QuestlineError

app = typer.Typer(
    name="questline",
    help="AI-native game test automation framework.",
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Print version"),
    ] = False,
) -> None:
    """Questline command-line interface."""


@app.command()
def doctor(
    profile: Annotated[
        str | None,
        typer.Option("--profile", "-p", help="Profile name from questline.toml"),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to questline.toml"),
    ] = None,
) -> None:
    """Print the resolved profile and key settings (no secrets)."""
    try:
        settings = load_settings(config_path=config, profile=profile)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    wait = settings.wait
    lines = [
        f"questline {__version__}",
        f"profile:     {settings.profile}",
        f"driver:      {settings.driver or '(unset)'}",
        f"device:      {settings.device or '(unset)'}",
        f"reporters:   {', '.join(settings.reporters) or '(none)'}",
        f"wait:        probe={wait.probe}s deadline={wait.deadline}s interval={wait.interval}s",
        f"log_json:    {settings.log_json}",
        f"project:     {settings.project_root}",
        f"store_db:    {settings.store_db}",
        f"artifacts:   {settings.artifacts_dir}",
        f"ledger:      {settings.ledger_path}",
    ]
    typer.echo("\n".join(lines))


if __name__ == "__main__":
    app()
