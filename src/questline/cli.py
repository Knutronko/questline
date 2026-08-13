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

lens_app = typer.Typer(
    name="lens",
    help="GameLens balance snapshot and diff (FP-G1).",
    no_args_is_help=True,
)
app.add_typer(lens_app, name="lens")

telemetry_app = typer.Typer(
    name="telemetry",
    help="Gameplay telemetry import and query (FP-G2).",
    no_args_is_help=True,
)
app.add_typer(telemetry_app, name="telemetry")


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
    typer.echo(f"questline hud -> http://{host}:{port}/  ({mode}; store={db_path})")
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


@lens_app.command("snapshot")
def lens_snapshot(
    pack: Annotated[
        Path | None,
        typer.Option(
            "--pack",
            help="Fixture/export pack dir (manifest.json + raw/*.json)",
        ),
    ] = None,
    import_file: Annotated[
        Path | None,
        typer.Option(
            "--import",
            help="Import an already-normalized balance_snapshot.json",
        ),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option("--version", "-V", help="game_version label (required with --pack)"),
    ] = None,
    snapshot_id: Annotated[
        str | None,
        typer.Option("--id", help="Snapshot id (default: game_version)"),
    ] = None,
    git_commit: Annotated[
        str | None,
        typer.Option("--git-commit", help="Optional git commit"),
    ] = None,
    feature_id: Annotated[
        str | None,
        typer.Option("--feature-id", help="Optional feature_id"),
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
    """Capture/import a balance snapshot into the store."""
    import json
    import re

    from questline.core.store import RunStore
    from questline.lens.snapshot import load_snapshot, normalize_pack, write_snapshot

    if (pack is None) == (import_file is None):
        typer.secho(
            "provide exactly one of --pack or --import",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        settings = load_settings(config_path=config, profile=profile)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    try:
        if pack is not None:
            if not version or not version.strip():
                typer.secho(
                    "--version is required with --pack",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=2)
            snap = normalize_pack(
                Path(pack),
                game_version=version.strip(),
                git_commit=git_commit,
                feature_id=feature_id,
            )
        else:
            assert import_file is not None
            snap = load_snapshot(Path(import_file))
            if version and version.strip():
                from dataclasses import replace

                from questline.lens.snapshot import BalanceSnapshot

                snap = BalanceSnapshot(
                    schema_version=snap.schema_version,
                    meta=replace(snap.meta, game_version=version.strip()),
                    entities=snap.entities,
                    supplementary=snap.supplementary,
                )
            if git_commit or feature_id:
                from dataclasses import replace

                from questline.lens.snapshot import BalanceSnapshot

                snap = BalanceSnapshot(
                    schema_version=snap.schema_version,
                    meta=replace(
                        snap.meta,
                        git_commit=git_commit or snap.meta.git_commit,
                        feature_id=feature_id or snap.meta.feature_id,
                    ),
                    entities=snap.entities,
                    supplementary=snap.supplementary,
                )
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    sid = (snapshot_id or snap.meta.game_version).strip()
    if not re.fullmatch(r"[A-Za-z0-9._:@+/-]+", sid):
        typer.secho(f"invalid snapshot id: {sid!r}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    db_path = Path(store_db) if store_db is not None else settings.store_db
    artifacts = (
        settings.artifacts_dir
        if store_db is None
        else (db_path.parent / "artifacts")
    )
    store = RunStore(db_path, artifacts_dir=artifacts)
    try:
        payload = json.dumps(snap.to_dict(), indent=2, sort_keys=True) + "\n"
        path = store.save_balance_snapshot(
            snapshot_id=sid,
            game_version=snap.meta.game_version,
            payload=payload,
            git_commit=snap.meta.git_commit,
            feature_id=snap.meta.feature_id,
            meta={
                "entity_count": len(snap.entities),
                "manifest_path": snap.meta.manifest_path,
            },
        )
        # Keep a copy next to import for debugging when --import was used.
        if import_file is None:
            write_snapshot(snap, path)
        typer.echo(f"snapshot id={sid} version={snap.meta.game_version} path={path}")
    finally:
        store.close()


@lens_app.command("diff")
def lens_diff(
    version_a: Annotated[str, typer.Argument(help="Left snapshot id or game_version")],
    version_b: Annotated[str, typer.Argument(help="Right snapshot id or game_version")],
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write report file"),
    ] = None,
    with_ai: Annotated[
        bool,
        typer.Option(
            "--ai/--no-ai",
            help="Include AI implications stub (pending phase-11)",
        ),
    ] = True,
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
    """Diff two stored balance snapshots (human text or machine JSON)."""
    import json
    from pathlib import Path as PathLib

    from questline.core.store import RunStore
    from questline.lens.diff import diff_snapshots
    from questline.lens.render import render_diff_text
    from questline.lens.report import implications_stub
    from questline.lens.snapshot import load_snapshot

    fmt = format.strip().lower()
    if fmt not in {"text", "json"}:
        typer.secho("--format must be 'text' or 'json'", fg=typer.colors.RED, err=True)
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

    artifacts = (
        settings.artifacts_dir
        if store_db is None
        else (db_path.parent / "artifacts")
    )
    store = RunStore(db_path, artifacts_dir=artifacts)
    try:
        row_a = store.get_balance_snapshot(version_a)
        row_b = store.get_balance_snapshot(version_b)
        if row_a is None:
            typer.secho(f"unknown snapshot: {version_a}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        if row_b is None:
            typer.secho(f"unknown snapshot: {version_b}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        path_a = PathLib(row_a["artifact_path"])
        path_b = PathLib(row_b["artifact_path"])
        try:
            snap_a = load_snapshot(path_a)
            snap_b = load_snapshot(path_b)
        except AuthoringError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc

        report = diff_snapshots(
            snap_a,
            snap_b,
            snapshot_id_a=row_a["id"],
            snapshot_id_b=row_b["id"],
        )
        implications = implications_stub(report) if with_ai else None
        if fmt == "json":
            payload = report.to_dict()
            if implications is not None:
                payload["implications"] = implications.to_dict()
            text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        else:
            text = render_diff_text(report, implications=implications)

        if output is not None:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            typer.echo(str(out_path))
        else:
            typer.echo(text, nl=False)
    finally:
        store.close()


@telemetry_app.command("import")
def telemetry_import(
    spool: Annotated[Path, typer.Argument(help="Path to telemetry spool JSON")],
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
    """Import a telemetry spool JSON into the store (replaces same session id)."""
    from questline.core.store import RunStore
    from questline.telemetry.ingest import ingest_spool_file

    try:
        settings = load_settings(config_path=config, profile=profile)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    db_path = Path(store_db) if store_db is not None else settings.store_db
    artifacts = (
        settings.artifacts_dir if store_db is None else (db_path.parent / "artifacts")
    )
    store = RunStore(db_path, artifacts_dir=artifacts)
    try:
        result = ingest_spool_file(store, Path(spool), source="import", replace=True)
    except AuthoringError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc
    except QuestlineError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    finally:
        store.close()
    typer.echo(
        f"session id={result['id']} version={result['game_version']} "
        f"events={result['event_count']} path={result['artifact_path']}"
    )


@telemetry_app.command("query")
def telemetry_query(
    session_id: Annotated[
        str | None,
        typer.Argument(help="Session id or unique prefix (omit to list)"),
    ] = None,
    version: Annotated[
        str | None,
        typer.Option("--version", "-V", help="Filter by game_version"),
    ] = None,
    snapshot: Annotated[
        str | None,
        typer.Option("--snapshot", help="Filter by config_snapshot_id"),
    ] = None,
    policy: Annotated[
        str | None,
        typer.Option("--policy", help="Filter by policy_id"),
    ] = None,
    seed: Annotated[
        str | None,
        typer.Option("--seed", help="Filter by seed"),
    ] = None,
    compare: Annotated[
        str | None,
        typer.Option("--compare", help="Second session id (diff summaries, b-a)"),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
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
    """List sessions, show one session summary, or compare two summaries."""
    import json

    from questline.core.store import RunStore
    from questline.telemetry.render import (
        render_compare,
        render_session_detail,
        render_session_list,
    )
    from questline.telemetry.summary import diff_summaries

    fmt = format.strip().lower()
    if fmt not in {"text", "json"}:
        typer.secho("--format must be 'text' or 'json'", fg=typer.colors.RED, err=True)
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

    artifacts = (
        settings.artifacts_dir if store_db is None else (db_path.parent / "artifacts")
    )
    store = RunStore(db_path, artifacts_dir=artifacts)
    try:
        if compare:
            if not session_id:
                typer.secho(
                    "query <id> --compare <idB> requires a first session id",
                    fg=typer.colors.RED,
                    err=True,
                )
                raise typer.Exit(code=2)
            row_a = store.get_telemetry_session(session_id)
            row_b = store.get_telemetry_session(compare)
            if row_a is None:
                typer.secho(f"unknown session: {session_id}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            if row_b is None:
                typer.secho(f"unknown session: {compare}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            deltas = diff_summaries(row_a.get("summary") or {}, row_b.get("summary") or {})
            payload = {
                "a": row_a["id"],
                "b": row_b["id"],
                "deltas": deltas,
            }
            text = (
                json.dumps(payload, indent=2, sort_keys=True) + "\n"
                if fmt == "json"
                else render_compare(row_a["id"], row_b["id"], deltas)
            )
            typer.echo(text, nl=False)
            return

        if session_id:
            row = store.get_telemetry_session(session_id)
            if row is None:
                typer.secho(f"unknown session: {session_id}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            n = store.count_telemetry_events(row["id"])
            if fmt == "json":
                out = dict(row)
                out["event_count"] = n
                out["events"] = store.list_telemetry_events(row["id"])
                typer.echo(json.dumps(out, indent=2, sort_keys=True) + "\n", nl=False)
            else:
                typer.echo(render_session_detail(row, n), nl=False)
            return

        rows = store.list_telemetry_sessions(
            game_version=version,
            config_snapshot_id=snapshot,
            policy_id=policy,
            seed=seed,
        )
        if fmt == "json":
            typer.echo(json.dumps(rows, indent=2, sort_keys=True) + "\n", nl=False)
        else:
            typer.echo(render_session_list(rows), nl=False)
    finally:
        store.close()


if __name__ == "__main__":
    app()
