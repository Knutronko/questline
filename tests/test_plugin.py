"""pytest plugin: quarantine exclusion, --feature filter, event wiring."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_toml(tmp_path: Path) -> Path:
    path = tmp_path / "questline.toml"
    path.write_text(
        '[profile.mock]\ndriver = "mock"\nwait.probe = 0.05\n'
        "wait.deadline = 0.5\nwait.interval = 0.01\n",
        encoding="utf-8",
    )
    return path


def test_quarantined_excluded_by_default(pytester: pytest.Pytester, sample_toml: Path) -> None:
    pytester.makepyfile(
        """
        import pytest

        def test_ok(questline_ctx):
            assert questline_ctx.run_id

        @pytest.mark.quest_quarantined
        def test_q(questline_ctx):
            assert False
        """
    )
    result = pytester.runpytest(
        f"--questline-config={sample_toml}",
        "--questline-profile=mock",
        "-q",
        "-o",
        "addopts=",
    )
    result.assert_outcomes(passed=1, deselected=1)


def test_include_quarantined(pytester: pytest.Pytester, sample_toml: Path) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.quest_quarantined
        def test_q(questline_ctx):
            assert True
        """
    )
    result = pytester.runpytest(
        f"--questline-config={sample_toml}",
        "--questline-profile=mock",
        "--include-quarantined",
        "-q",
        "-o",
        "addopts=",
    )
    result.assert_outcomes(passed=1)


def test_feature_filter(pytester: pytest.Pytester, sample_toml: Path) -> None:
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.feature("shop")
        def test_shop(questline_ctx):
            assert True

        @pytest.mark.feature("hud")
        def test_hud(questline_ctx):
            assert True

        def test_untagged(questline_ctx):
            assert True
        """
    )
    result = pytester.runpytest(
        f"--questline-config={sample_toml}",
        "--questline-profile=mock",
        "--feature=shop",
        "-q",
        "-o",
        "addopts=",
    )
    result.assert_outcomes(passed=1, deselected=2)


def test_feature_id_persisted_in_store(
    pytester: pytest.Pytester, sample_toml: Path, tmp_path: Path
) -> None:
    store_dir = tmp_path / "ql"
    store_dir.mkdir()
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.feature("pack-v2")
        def test_tagged(questline_ctx, questline_store, questline_run_id):
            assert questline_ctx.test_id
        """
    )
    config = Path(pytester.path) / "questline.toml"
    config.write_text(sample_toml.read_text(encoding="utf-8"), encoding="utf-8")
    result = pytester.runpytest(
        "--questline-config=questline.toml",
        "--questline-profile=mock",
        "-q",
        "-o",
        "addopts=",
    )
    result.assert_outcomes(passed=1)

    from questline.core.store import RunStore

    db = Path(pytester.path) / ".questline" / "store.db"
    assert db.is_file()
    with RunStore(db) as store:
        import sqlite3

        conn = sqlite3.connect(str(db))
        row = conn.execute("SELECT id FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        assert row is not None
        tests = store.list_tests(row[0])
        assert len(tests) == 1
        assert tests[0]["feature_id"] == "pack-v2"
        conn.close()


def test_failed_test_records_driver_health(pytester: pytest.Pytester, sample_toml: Path) -> None:
    pytester.makepyfile(
        """
        import pytest
        from questline.core.errors import AssertionFailedError

        def test_boom(questline_ctx):
            raise AssertionFailedError("nope")
        """
    )
    config = Path(pytester.path) / "questline.toml"
    config.write_text(sample_toml.read_text(encoding="utf-8"), encoding="utf-8")
    result = pytester.runpytest(
        "--questline-config=questline.toml",
        "--questline-profile=mock",
        "-q",
        "-o",
        "addopts=",
    )
    result.assert_outcomes(failed=1)
    from questline.core.store import RunStore

    db = Path(pytester.path) / ".questline" / "store.db"
    with RunStore(db) as store:
        import sqlite3

        conn = sqlite3.connect(str(db))
        tid = conn.execute("SELECT id FROM tests LIMIT 1").fetchone()[0]
        conn.close()
        dp = store.death_point(tid)
        assert dp["driver_health"] is not None
        assert "driver_alive" in dp["driver_health"]
