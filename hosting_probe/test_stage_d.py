"""Local tests of the stage D probe. No deployment, no account, no model-provider request.

The page tests need nothing. The database tests run only when a PostgreSQL URL is supplied in
ATLAS_PROBE_DATABASE_URL (a throwaway local database) and the psycopg driver is importable, e.g.:
    uv run --with "psycopg[binary]" python -m pytest hosting_probe/test_stage_d.py -q
Otherwise they are skipped, and nothing about the SQL is claimed as tested.
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from hosting_probe import check_publication
from hosting_probe.test_stage_a import _guard

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


URL = "postgresql://dbuser:dbpass-xyz@host-abc.invalid:5432/dbname"
CODE = "correct-probe-access-code-123"


@pytest.fixture
def fake_psycopg(monkeypatch):
    """A stand-in driver that counts connection attempts and always fails.

    The page imports psycopg only when the probe runs, so any call here is a database operation.
    """
    import types

    calls = []

    def connect(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("failure text containing host-abc.invalid and dbpass-xyz")

    module = types.ModuleType("psycopg")
    module.connect = connect
    monkeypatch.setitem(sys.modules, "psycopg", module)
    return calls


def _page(monkeypatch, secrets, typed=None):
    _guard(monkeypatch)  # also proves no outbound network on render
    at = AppTest.from_file(APP, default_timeout=30)
    for key, value in secrets.items():
        at.secrets[key] = value
    at.run()
    if typed is not None:
        at.text_input[0].set_value(typed).run()
    return at


def _everything_shown(at):
    return str([e.value for e in at.json] + [e.value for e in at.markdown])


@pytest.mark.parametrize(
    ("secrets", "typed", "expected_text"),
    [
        ({"DATABASE_URL": URL}, None, "Disabled: no PROBE_ACCESS_CODE"),  # fails closed
        (
            {"DATABASE_URL": URL, "PROBE_ACCESS_CODE": CODE},
            None,
            "Enter the probe access code",
        ),
        (
            {"DATABASE_URL": URL, "PROBE_ACCESS_CODE": CODE},
            "wrong-code",
            "Not authorized.",
        ),
        (
            {"DATABASE_URL": URL, "PROBE_ACCESS_CODE": CODE},
            CODE[:-1],
            "Not authorized.",
        ),
        ({"PROBE_ACCESS_CODE": CODE}, None, "skipped"),  # no database configured
    ],
    ids=[
        "no_code_configured",
        "nothing_typed",
        "wrong_code",
        "near_miss",
        "no_database_url",
    ],
)
def test_no_database_operation_without_successful_authorization(
    monkeypatch, fake_psycopg, secrets, typed, expected_text
):
    """A signed-out visitor to the public page cannot start the database tests."""
    at = _page(monkeypatch, secrets, typed)

    assert not at.exception
    assert expected_text in _everything_shown(at)
    assert len(at.button) == 0  # nothing to press, so nothing can run
    assert fake_psycopg == []  # and no connection was attempted
    assert URL not in _everything_shown(at) and CODE not in _everything_shown(at)


def test_correct_code_enables_the_probe_and_failures_show_only_the_error_type(
    monkeypatch, fake_psycopg
):
    at = _page(
        monkeypatch, {"DATABASE_URL": URL, "PROBE_ACCESS_CODE": CODE}, typed=CODE
    )
    assert (
        len(at.button) == 1 and fake_psycopg == []
    )  # authorized, but nothing runs until pressed

    at.button[0].click().run()

    shown = _everything_shown(at)
    assert len(fake_psycopg) >= 1  # now, and only now, a connection is attempted
    assert "stopped: RuntimeError" in shown
    for secret_text in ("host-abc.invalid", "dbpass-xyz", "dbuser", CODE):
        assert secret_text not in shown


def test_code_comparison_is_exact_and_rejects_empty_input():
    spec = importlib.util.spec_from_file_location("stage_d_app_helpers", APP)
    source = Path(APP).read_text(encoding="utf-8")
    start = source.index("def code_matches")
    end = source.index("def run_budget_probe")
    namespace = {"hmac": __import__("hmac")}
    exec(source[start:end], namespace)  # noqa: S102 - the helper only, from our own file
    match = namespace["code_matches"]
    assert spec is not None
    assert match("abc", "abc") and not match("", "abc") and not match("abd", "abc")
    assert not match("abc", "abcd") and not match("", "")


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
