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

quarantine_app = typer.Typer(
    name="quarantine",
    help="Manage the versioned quarantine ledger (quarantine.yaml).",
    no_args_is_help=True,
)
app.add_typer(quarantine_app, name="quarantine")

perf_app = typer.Typer(
    name="perf",
    help="PerfProbe reports and helpers (phase-09).",
    no_args_is_help=True,
)
app.add_typer(perf_app, name="perf")


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
        f"target_port: {settings.target_port}",
        f"target_plat:  {settings.target_platform or '(unset)'}",
        f"device_serial:{settings.device_serial or '(auto)'}",
        f"apk_path:    {settings.apk_path or '(unset)'}",
        f"app_package: {settings.app_package or '(unset)'}",
        f"emulator_avd:{settings.emulator_avd or '(unset)'}",
        f"project:     {settings.project_root}",
        f"store_db:    {settings.store_db}",
        f"artifacts:   {settings.artifacts_dir}",
        f"ledger:      {settings.ledger_path}",
        (
            f"perf:        enabled={settings.perf.enabled} "
            f"interval={settings.perf.interval_s}s "
            f"scope={settings.perf.scope} source={settings.perf.source}"
        ),
    ]
    typer.echo("\n".join(lines))


def _ledger_path(path: Path | None) -> Path:
    return path if path is not None else Path.cwd() / "quarantine.yaml"


@quarantine_app.command("add")
def quarantine_add(
    test_id: Annotated[str, typer.Argument(help="Pytest nodeid to quarantine")],
    reason: Annotated[str, typer.Option("--reason", "-r", help="Why it is quarantined")],
    owner: Annotated[str, typer.Option("--owner", "-o", help="Owner responsible for exit")],
    exit_criteria: Annotated[
        str,
        typer.Option("--exit-criteria", "-e", help="When it may leave quarantine"),
    ],
    issue: Annotated[
        str | None,
        typer.Option("--issue", "-i", help="Linked issue URL or id"),
    ] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", "-f", help="Optional feature id"),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Path to quarantine.yaml"),
    ] = None,
) -> None:
    """Add or update a quarantine ledger entry."""
    from questline.authoring.quarantine import QuarantineLedger

    ledger_file = _ledger_path(path)
    try:
        ledger = QuarantineLedger.load(ledger_file)
        ledger.add(
            test_id,
            reason=reason,
            owner=owner,
            exit_criteria=exit_criteria,
            issue=issue,
            feature=feature,
        )
        ledger.save()
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"quarantine: added {test_id} → {ledger_file}")


@quarantine_app.command("remove")
def quarantine_remove(
    test_id: Annotated[str, typer.Argument(help="Pytest nodeid to remove")],
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Path to quarantine.yaml"),
    ] = None,
) -> None:
    """Remove a quarantine ledger entry."""
    from questline.authoring.quarantine import QuarantineLedger

    ledger_file = _ledger_path(path)
    try:
        ledger = QuarantineLedger.load(ledger_file)
        if not ledger.remove(test_id):
            typer.secho(f"quarantine: no entry for {test_id}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        ledger.save()
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"quarantine: removed {test_id} from {ledger_file}")


@quarantine_app.command("audit")
def quarantine_audit(
    path: Annotated[
        Path | None,
        typer.Option("--path", help="Path to quarantine.yaml"),
    ] = None,
    tests: Annotated[
        list[str] | None,
        typer.Option("--tests", help="Test path(s) to collect markers from"),
    ] = None,
    rootdir: Annotated[
        Path | None,
        typer.Option("--rootdir", help="Pytest rootdir for collection"),
    ] = None,
) -> None:
    """Fail (exit 1) on limbo: marker↔ledger mismatch."""
    from questline.authoring.quarantine import QuarantineLedger, collect_quarantined_nodeids

    ledger_file = _ledger_path(path)
    try:
        ledger = QuarantineLedger.load(ledger_file)
        marked = collect_quarantined_nodeids(
            tests,
            rootdir=rootdir or Path.cwd(),
        )
        report = ledger.audit(marked)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(report.summary())
    if not report.ok:
        raise typer.Exit(code=1)


@app.command()
def hud(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="TCP port (default 8741)"),
    ] = 8741,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Bind address (default 127.0.0.1; opt-in for non-localhost)",
        ),
    ] = "127.0.0.1",
    open_browser: Annotated[
        bool,
        typer.Option("--open", help="Open the HUD in the default browser"),
    ] = False,
    read_only: Annotated[
        bool,
        typer.Option(
            "--read-only",
            help="Viewer mode: disable launcher/quarantine/config mutators",
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to questline.toml"),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile name (for store path resolution)"),
    ] = None,
    store_db: Annotated[
        Path | None,
        typer.Option("--store", help="Override path to store.db"),
    ] = None,
) -> None:
    """Serve the local HUD control center (viewer + launcher when not --read-only)."""
    try:
        from questline.hud.server import serve
    except ImportError as exc:
        typer.secho(
            "HUD requires: pip install 'questline[hud]'",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from exc

    try:
        settings = load_settings(config_path=config, profile=profile)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    db_path = Path(store_db) if store_db is not None else settings.store_db
    from questline.core.events import EventBus
    from questline.core.store import RunStore

    store = RunStore(
        db_path,
        artifacts_dir=settings.artifacts_dir,
        ledger_path=settings.ledger_path,
    )
    bus = EventBus()
    store.attach(bus)
    mode = "read-only viewer" if read_only else "control center"
    typer.echo(f"questline hud → http://{host}:{port}/  ({mode}; store={db_path})")
    try:
        serve(
            store=store,
            bus=bus,
            host=host,
            port=port,
            open_browser=open_browser,
            read_only=read_only,
            project_root=settings.project_root,
            config_path=config or (settings.project_root / "questline.toml"),
            quarantine_path=settings.project_root / "quarantine.yaml",
        )
    finally:
        store.close()


@perf_app.command("report")
def perf_report(
    run_id: Annotated[str, typer.Argument(help="Run id to summarize")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or html"),
    ] = "text",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Write report file (default: print text / artifacts dir)"
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Path to questline.toml"),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option("--profile", "-p", help="Profile name (for store path resolution)"),
    ] = None,
    store_db: Annotated[
        Path | None,
        typer.Option("--store", help="Override path to store.db"),
    ] = None,
) -> None:
    """Print or write a PerfProbe summary for a run."""
    from questline.core.store import RunStore
    from questline.perf.report import render_perf_report, write_perf_report

    fmt = format.strip().lower()
    if fmt not in {"text", "html"}:
        typer.secho("--format must be 'text' or 'html'", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    try:
        settings = load_settings(config_path=config, profile=profile)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    db_path = Path(store_db) if store_db is not None else settings.store_db
    if not db_path.is_file():
        typer.secho(f"store not found: {db_path}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    store = RunStore(db_path, artifacts_dir=settings.artifacts_dir)
    try:
        if store.get_run(run_id) is None:
            typer.secho(f"unknown run_id: {run_id}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        samples = store.list_perf_samples(run_id=run_id)
        if output is not None:
            out_path = Path(output)
            if out_path.suffix.lower() in {".html", ".htm"}:
                fmt = "html"
            elif out_path.suffix.lower() in {".txt", ".md"}:
                fmt = "text"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                render_perf_report(run_id=run_id, samples=samples, fmt=fmt),  # type: ignore[arg-type]
                encoding="utf-8",
            )
            typer.echo(str(out_path))
        elif fmt == "html":
            path = write_perf_report(
                run_id=run_id,
                samples=samples,
                output_dir=settings.artifacts_dir,
                fmt="html",
            )
            typer.echo(str(path))
        else:
            typer.echo(render_perf_report(run_id=run_id, samples=samples, fmt="text"), nl=False)
    finally:
        store.close()


if __name__ == "__main__":
    app()
