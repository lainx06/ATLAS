"""Local tests of the stage D probe. No deployment, no account, no model-provider request.

The page tests need nothing. The database tests run only when a PostgreSQL URL is supplied in
ATLAS_PROBE_DATABASE_URL (a throwaway local database) and the psycopg driver is importable, e.g.:
    uv run --with "psycopg[binary]" python -m pytest hosting_probe/test_stage_d.py -q
Otherwise they are skipped, and nothing about the SQL is claimed as tested.
"""

import importlib
import os
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from hosting_probe import check_publication
from hosting_probe.test_stage_a import _guard, _shown

STAGE_D = Path(__file__).with_name("stage_d")
APP = str(STAGE_D / "app.py")
DATABASE_URL = os.environ.get("ATLAS_PROBE_DATABASE_URL")


def test_publication_set_is_exactly_the_three_clean_files():
    assert check_publication.problems("stage_d") == []


def test_page_renders_without_a_database_url_and_without_network(monkeypatch):
    _guard(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("skipped" in m.value for m in at.markdown)


def test_database_url_alone_causes_no_connection_and_is_not_shown(monkeypatch):
    """Nothing connects until the button is pressed; the URL is never rendered."""
    _guard(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets["DATABASE_URL"] = "not-a-real-url-for-test"
    at.run()
    assert not at.exception
    assert "not-a-real-url-for-test" not in _shown(at)
    assert len(at.button) == 1


def test_a_failed_connection_reports_only_the_error_type(monkeypatch):
    """With the button pressed and an unusable URL, no secret or host text is shown."""
    pytest.importorskip("psycopg")
    _guard(monkeypatch)
    at = AppTest.from_file(APP, default_timeout=30)
    at.secrets["DATABASE_URL"] = (
        "postgresql://user:pw@db.invalid:5432/x"  # a name that cannot resolve
    )
    at.run()
    at.button[0].click().run()
    shown = str([e.value for e in at.json])
    assert "stopped:" in shown and "pw@" not in shown and "db.invalid" not in shown


@pytest.fixture(scope="module")
def budget_probe():
    sys.path.insert(0, str(STAGE_D))
    try:
        yield importlib.import_module("budget_probe")
    finally:
        sys.path.remove(str(STAGE_D))


@pytest.mark.skipif(not DATABASE_URL, reason="no throwaway database supplied")
def test_every_budget_scenario_passes_on_a_real_database(budget_probe):
    psycopg = pytest.importorskip("psycopg")

    def connect():
        return psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=15)

    results = budget_probe.run_all(connect)

    failed = [r for r in results if not r["ok"]]
    assert not failed, failed
    assert len(results) == 7
