"""T-12 step 2: the budget store against a disposable local PostgreSQL (like stage D).

    $env:ATLAS_REQUIRE_DOCKER='1'; uv run --locked pytest tests/hosted -q

These are local PostgreSQL 17 results, not evidence of Neon connectivity or hosted
concurrency. No provider request is made.
"""

import threading
from datetime import date
from decimal import Decimal

import psycopg
import pytest

from atlas.agent.budget import ReservationRefused
from atlas.hosted import access
from atlas.hosted import budget_store as bs

CEILING = Decimal("0.0108")  # one request at the decided ceilings
DAY1, DAY2 = date(2026, 10, 18), date(2026, 10, 19)
ROUNDS = 10


def store(url, day=DAY1):
    s = bs.BudgetStore(bs.connector(url), today=lambda: day)
    s.setup()
    return s


def set_cap(url, key, cap=None, spent=None):
    with psycopg.connect(url, autocommit=True) as conn:
        if cap is not None:
            conn.execute(
                "UPDATE atlas_cap SET cap_usd = %s WHERE cap_key = %s", (cap, key)
            )
        if spent is not None:
            conn.execute(
                "UPDATE atlas_cap SET spent_usd = %s WHERE cap_key = %s", (spent, key)
            )


def rows(url, sql, params=()):
    with psycopg.connect(url, autocommit=True) as conn:
        return conn.execute(sql, params).fetchall()


def caps(url):
    return {
        k: (cap, reserved, spent, requests)
        for k, cap, reserved, spent, requests in rows(
            url,
            "SELECT cap_key, cap_usd, reserved_usd, spent_usd, requests FROM atlas_cap",
        )
    }


def race(calls):
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(i):
        try:
            barrier.wait(timeout=30)
            results[i] = calls[i]()
        except ReservationRefused as exc:
            results[i] = f"refused:{exc.code}"
        except Exception as exc:  # noqa: BLE001 - recorded as that call's result
            results[i] = f"error:{type(exc).__name__}"

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(calls))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def test_the_decided_caps_are_created_once(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    state = caps(database_url)
    assert state["public"][0] == Decimal("3.00")
    assert state["public_daily:2026-10-18"][0] == Decimal("1.00")
    assert state[f"session:{session.session_id}"][0] == Decimal("0.0648")
    s.open_session(bs.JUDGE, CEILING)
    assert caps(database_url)["judge"][0] == Decimal("5.00")
    # An operator's change in the database is authoritative: never reset by the app.
    set_cap(database_url, "public", cap=Decimal("2.50"))
    s.open_session(bs.PUBLIC, CEILING)
    assert caps(database_url)["public"][0] == Decimal("2.50")
    assert (
        sum(bs.HOSTED_DECIDED[k] for k in ("public_pool_usd", "judge_pool_usd"))
        == (bs.HOSTED_DECIDED["total_usd"])
    )


def test_concurrent_sessions_race_for_the_last_pool_dollars(database_url):
    """Two sessions on separate connections race for a pool that admits one request."""
    s = store(database_url)
    for n in range(ROUNDS):
        a = s.open_session(bs.PUBLIC, CEILING)
        b = s.open_session(bs.PUBLIC, CEILING)
        # Leave exactly 1.5 ceilings in the public pool.
        state = caps(database_url)["public"]
        set_cap(database_url, "public", cap=state[1] + state[2] + CEILING * 3 / 2)
        sa, sb = store(database_url), store(database_url)
        got = race(
            [
                lambda st=st, sess=sess: st.reserve(
                    f"{sess.session_id}:a1", bs.PUBLIC, sess.session_id, CEILING
                )
                for st, sess in ((sa, a), (sb, b))
            ]
        )
        assert sorted(got) == ["refused:public", "reserved"], (n, got)
        held = rows(
            database_url,
            "SELECT count(*) FROM atlas_reservation WHERE request_id IN (%s, %s)",
            (f"{a.session_id}:a1", f"{b.session_id}:a1"),
        )[0][0]
        assert held == 1
        for x in (sa, sb):
            x.close()
        # settle the admitted one so the next round starts from settled spending
        winner = a if got[0] == "reserved" else b
        s.dispatched(f"{winner.session_id}:a1")
        assert s.settle(f"{winner.session_id}:a1", Decimal("0.001")) == "settled"


def test_a_refused_reservation_leaves_no_partial_change(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    set_cap(database_url, "public_daily:2026-10-18", cap=Decimal("0.005"))
    before = caps(database_url)
    with pytest.raises(ReservationRefused) as refused:
        s.reserve("r1", bs.PUBLIC, session.session_id, CEILING)
    assert refused.value.code == "public_daily"
    assert caps(database_url) == before  # public and the session row unchanged too
    assert rows(database_url, "SELECT * FROM atlas_reservation") == []
    events = [e[2] for e in s.events()]
    assert "refused:public_daily" in events


def test_the_daily_cap_resets_by_date(database_url):
    s1 = store(database_url, DAY1)
    a = s1.open_session(bs.PUBLIC, CEILING)
    set_cap(database_url, "public_daily:2026-10-18", spent=Decimal("0.995"))
    with pytest.raises(ReservationRefused) as refused:
        s1.reserve("d1", bs.PUBLIC, a.session_id, CEILING)
    assert refused.value.code == "public_daily"
    with pytest.raises(ReservationRefused):
        s1.open_session(bs.PUBLIC, CEILING)  # the page says the budget is reached
    s2 = store(database_url, DAY2)
    b = s2.open_session(bs.PUBLIC, CEILING)
    assert s2.reserve("d2", bs.PUBLIC, b.session_id, CEILING) == "reserved"
    state = caps(database_url)
    assert state["public_daily:2026-10-19"][1] == CEILING
    assert state["public_daily:2026-10-18"][2] == Decimal("0.995")  # still on record
    assert state["public"][1] == CEILING


def test_the_session_caps_requests_and_dollars(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    for n in range(1, 7):  # 6 x 0.0108 = 0.0648 exactly
        assert session.reserve(n, CEILING) == f"{session.session_id}:a{n}"
    with pytest.raises(ReservationRefused) as refused:
        session.reserve(7, CEILING)
    assert refused.value.code in ("session_requests", "session_budget")
    # a released (never sent) request no longer counts against the request limit
    session.release(f"{session.session_id}:a6")
    assert session.reserve(8, CEILING)
    other = s.open_session(bs.PUBLIC, CEILING)
    for n in range(1, 7):
        other.reserve(n, Decimal("0.001"))
    with pytest.raises(ReservationRefused) as refused:
        other.reserve(7, Decimal("0.001"))
    assert refused.value.code == "session_requests"


def test_public_exhaustion_leaves_the_judge_pool(database_url):
    s = store(database_url)
    s.open_session(bs.PUBLIC, CEILING)
    set_cap(database_url, "public", spent=Decimal("3.00"))
    with pytest.raises(ReservationRefused) as refused:
        s.open_session(bs.PUBLIC, CEILING)
    assert refused.value.code == "public"
    judge = s.open_session(bs.JUDGE, CEILING)
    assert judge.reserve(1, CEILING)
    state = caps(database_url)
    assert state["judge"][1] == CEILING
    assert state["public"][1] == 0


@pytest.mark.parametrize(
    "typed", ["judge-code-correct-1234", "wrong-code-xyz-5678", ""]
)
def test_the_judge_route_by_access_code(database_url, typed):
    s = store(database_url)
    expected = "judge-code-correct-1234"
    route = access.select_route(typed, expected, s.log_event)
    events = s.events()
    if typed == expected:
        assert route == bs.JUDGE
        assert [e[1:3] for e in events] == [("judge", access.ACCEPTED)]
    elif typed:
        assert route == bs.PUBLIC  # a wrong code falls back to the public route
        assert [e[1:3] for e in events] == [("judge", access.REJECTED)]
    else:
        assert route == bs.PUBLIC
        assert events == []
    # Only time, route, event code and amount are stored; no typed or configured text.
    dump = str(rows(database_url, "SELECT * FROM atlas_event"))
    assert expected not in dump and (not typed or typed not in dump)
    assert [c[0] for c in rows(
        database_url,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'atlas_event' ORDER BY ordinal_position",
    )] == ["id", "time", "route", "event", "amount_usd"]  # fmt: skip


def test_events_accept_only_fixed_codes(database_url):
    s = store(database_url)
    for bad in ("free text with spaces", "sk-key=value", "x" * 0 + "a b"):
        with pytest.raises(ValueError):
            s.log_event(bs.PUBLIC, bad)
    with pytest.raises(ValueError):
        s.log_event("other_route", "reserved")


def test_dispatched_unknown_usage_is_held_and_never_released(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    rid = session.reserve(1, CEILING)
    session.dispatched(rid)
    session.hold(rid)  # unknown usage: held at the request ceiling
    s.close()
    fresh = store(database_url)  # a new connection stands for a restart
    assert fresh.release(rid) == "retained-dispatched"
    assert fresh.reservation(rid)[0] == "dispatched"
    assert caps(database_url)["public"][1] == CEILING
    # It blocks a request the pool could only take without it.
    set_cap(database_url, "public", cap=CEILING * 3 / 2)
    with pytest.raises(ReservationRefused):
        fresh.reserve("other", bs.PUBLIC, session.session_id, CEILING)
    assert fresh.prune(1) == {"reservations": 0, "events": 0}
    assert (
        fresh.reservation(rid)[0] == "dispatched"
    )  # never pruned before reconciliation
    assert (
        fresh.settle(rid, Decimal("0.0021")) == "settled"
    )  # an operator's reconciliation
    assert caps(database_url)["public"][1:3] == (0, Decimal("0.0021"))


def test_settle_is_idempotent_by_request_id(database_url):
    s = store(database_url)
    session = s.open_session(bs.JUDGE, CEILING)
    rid = session.reserve(1, CEILING)
    session.dispatched(rid)
    s1, s2 = store(database_url), store(database_url)
    got = race([lambda: s1.settle(rid, Decimal("0.0016272"))] + [
        lambda: s2.settle(rid, Decimal("0.0016272"))
    ])  # fmt: skip
    assert sorted(got) == ["already-settled", "settled"]
    state = caps(database_url)
    assert state["judge"][1:3] == (0, Decimal("0.0016272"))  # exact Decimal, once
    assert state[f"session:{session.session_id}"][1:3] == (0, Decimal("0.0016272"))
    assert s.settle(rid, Decimal("0.5")) == "already-settled"
    assert caps(database_url)["judge"][2] == Decimal("0.0016272")


def test_a_repeated_request_id_never_reserves_twice(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    s1, s2 = store(database_url), store(database_url)
    sid = session.session_id
    got = race([lambda: s1.reserve("dup", bs.PUBLIC, sid, CEILING)] + [
        lambda: s2.reserve("dup", bs.PUBLIC, sid, CEILING)
    ])  # fmt: skip
    assert sorted(g.split(":")[0] for g in got) == ["duplicate", "reserved"]
    assert caps(database_url)["public"][1] == CEILING
    with pytest.raises(bs.StoreError):  # the session binding refuses to send twice
        session.reserve(1, CEILING)
        session.reserve(1, CEILING)


def test_known_usage_above_the_reservation_is_charged_exactly(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    rid = session.reserve(1, CEILING)
    session.dispatched(rid)
    assert s.settle(rid, Decimal("0.0200001")) == "settled"
    assert caps(database_url)["public"][1:3] == (0, Decimal("0.0200001"))


def test_release_only_before_dispatch(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    rid = session.reserve(1, CEILING)
    assert s.release(rid) == "released"
    assert caps(database_url)["public"][1] == 0
    assert s.release(rid) == "invalid-state:released"
    with pytest.raises(bs.StoreError):
        s.dispatched(rid)  # a released reservation can never be sent


def test_many_concurrent_requests_keep_the_totals_consistent(database_url):
    """Sessions on both routes reserving at once: no deadlock, totals add up."""
    s = store(database_url)
    sessions = [s.open_session(bs.PUBLIC, CEILING) for _ in range(4)] + [
        s.open_session(bs.JUDGE, CEILING) for _ in range(2)
    ]
    stores = [store(database_url) for _ in range(len(sessions) * 2)]
    calls = []
    for i, sess in enumerate(sessions):
        for j in (1, 2):
            st = stores[i * 2 + j - 1]
            calls.append(
                lambda st=st, sess=sess, j=j: st.reserve(
                    f"{sess.session_id}:a{j}", sess.route, sess.session_id, CEILING
                )
            )
    got = race(calls)
    assert got == ["reserved"] * len(calls), got
    state = caps(database_url)
    assert state["public"][1] == CEILING * 8
    assert state["public_daily:2026-10-18"][1] == CEILING * 8
    assert state["judge"][1] == CEILING * 4
    for x in stores:
        x.close()


def test_prune_deletes_only_resolved_rows(database_url):
    s = store(database_url)
    session = s.open_session(bs.PUBLIC, CEILING)
    settled = session.reserve(1, CEILING)
    session.dispatched(settled)
    session.settle(settled, Decimal("0.001"))
    released = session.reserve(2, CEILING)
    session.release(released)
    open_ = session.reserve(3, CEILING)
    session.dispatched(open_)
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE atlas_reservation SET updated_at = now() - interval '40 days'"
        )
        conn.execute("UPDATE atlas_event SET time = now() - interval '40 days'")
    before = caps(database_url)
    result = s.prune(30)
    assert result["reservations"] == 2 and result["events"] > 0
    left = rows(database_url, "SELECT request_id, state FROM atlas_reservation")
    assert left == [(open_, "dispatched")]
    assert caps(database_url) == before  # cumulative spending is never reset
