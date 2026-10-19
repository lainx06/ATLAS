"""T-12 step 2: one hosted live session end to end, against the disposable local PostgreSQL
and a mocked Token Factory (no request leaves the process; nothing reaches Neon or Nebius).

Covers the fail-closed order (kill switch, configuration, store, route, caps, pre-run check),
the judge route, exhaustion, and that the store's totals equal the run's own ledger.
"""

from decimal import Decimal

import hosted_helpers as H
import psycopg
import pytest

from atlas.agent import controller as ctl
from atlas.agent.network import deny_network
from atlas.hosted import budget_store as bs
from atlas.hosted import session as hs


def secrets_for(url, **overrides):
    values = {
        "NEBIUS_API_KEY": H.KEY,
        "DATABASE_URL": url,
        "JUDGE_ACCESS_CODE": H.JUDGE_CODE,
        "HOSTED_LIVE_ENABLED": "true",
        **overrides,
    }
    return lambda name: values.get(name)


def run(monkeypatch, tmp_path, secret, typed=None, provider=None, factory=None):
    provider = provider or H.live6_provider()
    H.wire(monkeypatch, provider)
    with deny_network():  # Python networking is denied; libpq reaches the local server
        outcome = hs.run_live_session(
            secret, typed, runs_dir=tmp_path / "runs", store_factory=factory
        )
    return outcome, provider


def query(url, sql):
    with psycopg.connect(url, autocommit=True) as conn:
        return conn.execute(sql).fetchall()


def test_a_public_session_runs_and_the_store_matches_the_ledger(
    database_url, monkeypatch, tmp_path
):
    outcome, provider = run(monkeypatch, tmp_path, secrets_for(database_url))
    assert outcome.status == "ran" and outcome.route == bs.PUBLIC
    assert outcome.terminal_state == ctl.REPORT
    assert len(provider.gets()) == 1 and len(provider.posts()) == 4  # pre-run check + 4
    report = __import__("json").loads(
        (outcome.run_dir / "agent_report.json").read_text(encoding="utf-8")
    )
    assert report["proposals"][0]["outcome"] == "not_executed_here"
    known = Decimal(report["cost"]["known_usd"])
    assert known == H.USAGE_USD * 4
    states = query(database_url, "SELECT state, actual_usd FROM atlas_reservation")
    assert sorted(s for s, _ in states) == ["settled"] * 4
    assert sum(a for _, a in states) == known
    caps = dict(query(database_url, "SELECT cap_key, spent_usd FROM atlas_cap"))
    assert caps["public"] == known
    daily = [k for k in caps if k.startswith("public_daily:")]
    assert len(daily) == 1 and caps[daily[0]] == known
    assert "judge" not in caps  # a public session never touches the judge pool


@pytest.mark.parametrize(
    "value", [None, "", "false", "True", "TRUE", "1", "yes", " true", "true "]
)
def test_the_kill_switch_must_be_exactly_true(
    database_url, monkeypatch, tmp_path, value
):
    calls = []

    def factory(url):
        calls.append(url)
        raise AssertionError("the store must not be contacted")

    outcome, provider = run(
        monkeypatch, tmp_path, secrets_for(database_url, HOSTED_LIVE_ENABLED=value),
        factory=factory,
    )  # fmt: skip
    assert outcome.status == "unavailable" and outcome.code == "live_disabled"
    assert outcome.message == hs.UNAVAILABLE_MESSAGE
    assert provider.requests == [] and calls == []


@pytest.mark.parametrize(
    ("name", "code"), [("DATABASE_URL", "no_database"), ("NEBIUS_API_KEY", "no_key")]
)
def test_missing_configuration_sends_nothing(monkeypatch, tmp_path, name, code):
    secret = secrets_for("postgresql://u:p@127.0.0.1:1/x", **{name: None})
    outcome, provider = run(monkeypatch, tmp_path, secret)
    assert (outcome.status, outcome.code) == ("unavailable", code)
    assert provider.requests == []


def test_an_unreachable_store_sends_nothing(monkeypatch, tmp_path, postgres_server):
    host, port, user, _ = postgres_server
    bad = f"postgresql://{user}:wrong-{H.DB_PASSWORD_MARKER}@{host}:{port}/atlas_test"
    outcome, provider = run(monkeypatch, tmp_path, secrets_for(bad))
    assert (outcome.status, outcome.code) == ("unavailable", "store_unavailable")
    assert provider.requests == []
    closed = "postgresql://u:p@127.0.0.1:9/none"  # nothing listens on the discard port
    outcome, provider = run(monkeypatch, tmp_path, secrets_for(closed))
    assert (outcome.status, outcome.code) == ("unavailable", "store_unavailable")
    assert provider.requests == []


def test_the_judge_route_with_the_correct_code(database_url, monkeypatch, tmp_path):
    outcome, _ = run(
        monkeypatch, tmp_path, secrets_for(database_url), typed=H.JUDGE_CODE
    )
    assert outcome.status == "ran" and outcome.route == bs.JUDGE
    caps = dict(query(database_url, "SELECT cap_key, spent_usd FROM atlas_cap"))
    assert caps["judge"] == H.USAGE_USD * 4
    assert "public" not in caps
    events = query(database_url, "SELECT route, event FROM atlas_event ORDER BY id")
    assert events[0] == ("judge", "judge_code_accepted")


def test_a_wrong_code_uses_the_public_route_and_is_logged_without_text(
    database_url, monkeypatch, tmp_path
):
    typed = "wrong-" + H.JUDGE_CODE[:10]
    outcome, _ = run(monkeypatch, tmp_path, secrets_for(database_url), typed=typed)
    assert outcome.status == "ran" and outcome.route == bs.PUBLIC
    events = query(database_url, "SELECT route, event FROM atlas_event ORDER BY id")
    assert events[0] == ("judge", "judge_code_rejected")
    everything = str(query(database_url, "SELECT * FROM atlas_event")) + str(
        query(database_url, "SELECT * FROM atlas_cap")
    ) + str(query(database_url, "SELECT * FROM atlas_reservation"))  # fmt: skip
    for marker in (typed, H.JUDGE_CODE, H.KEY):
        assert marker not in everything


def test_daily_exhaustion_is_reported_and_nothing_spends(
    database_url, monkeypatch, tmp_path
):
    outcome, _ = run(monkeypatch, tmp_path, secrets_for(database_url))
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE atlas_cap SET spent_usd = cap_usd WHERE cap_key LIKE 'public_daily:%'"
        )
    outcome, provider = run(monkeypatch, tmp_path, secrets_for(database_url))
    assert outcome.status == "exhausted" and outcome.code == "public_daily"
    assert outcome.message == (
        "Live demo budget reached for today; recorded runs remain available."
    )
    assert provider.requests == []  # not even the pre-run check
    # The judge route still works after the public budget is exhausted.
    outcome, provider = run(
        monkeypatch, tmp_path, secrets_for(database_url), typed=H.JUDGE_CODE
    )
    assert outcome.status == "ran" and outcome.route == bs.JUDGE


def test_the_kill_switch_stops_a_session_before_its_next_request(
    database_url, monkeypatch, tmp_path
):
    values = {"on": "true"}
    base = secrets_for(database_url)

    def secret(name):
        return values["on"] if name == "HOSTED_LIVE_ENABLED" else base(name)

    def switch_off_after_two(request):
        if len(provider.posts()) == 2:
            values["on"] = "false"

    provider = H.live6_provider(on_post=switch_off_after_two)
    outcome, _ = run(monkeypatch, tmp_path, secret, provider=provider)
    assert outcome.status == "ran" and outcome.terminal_state == ctl.BUDGET_EXHAUSTED
    assert len(provider.posts()) == 2
    assert outcome.code == "exhausted"
    states = query(database_url, "SELECT state FROM atlas_reservation")
    assert sorted(s for (s,) in states) == ["settled", "settled"]


def test_a_failed_pre_run_check_sends_no_completion(
    database_url, monkeypatch, tmp_path
):
    listing = __import__("copy").deepcopy(H.LISTING)
    for m in listing["data"]:
        if m["id"] == H.MODEL:
            m["pricing"] = {**m.get("pricing", {}), "prompt": "0.0000004"}

    class Changed(H.Provider):
        def __call__(self, request):
            if request.method == "GET":
                self.requests.append(request)
                import json

                import httpx2

                return httpx2.Response(200, content=json.dumps(listing).encode())
            return super().__call__(request)

    provider = Changed([H.completion(H.FINISH)])
    outcome, _ = run(
        monkeypatch, tmp_path, secrets_for(database_url), provider=provider
    )
    assert (outcome.status, outcome.code) == ("unavailable", "preflight_abort")
    assert provider.posts() == []
    assert query(database_url, "SELECT count(*) FROM atlas_reservation") == [(0,)]
