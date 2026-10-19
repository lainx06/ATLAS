"""The server-side budget store for hosted live sessions (T-12 step 2; Neon Postgres).

Built on the design proven by the stage D probe (`hosting_probe/stage_d/budget_probe.py`,
`docs/HOSTING_PROBE.md` §5a-5b), with money instead of synthetic units. Every cap is enforced
here, on the server, and the store fails closed: if it cannot be reached or answers anything
unexpected, no request is sent.

**Caps** (rows of `atlas_cap`; DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 3):

- `public`: the public pool, $3.00 in total;
- `public_daily:<YYYY-MM-DD>`: the public daily cap, $1.00 per UTC day (a new row each day,
  so the cap resets by date and earlier days stay on record);
- `judge`: the judge pool, $5.00, reachable only with the private access code;
- `session:<id>`: one live session, the decided estimate cap $0.0648 and at most 6 requests.

A request on the public route is reserved against `public`, today's `public_daily` and its
session; on the judge route against `judge` and its session. Public traffic therefore cannot
exhaust the judge pool. Cap rows are created once (`INSERT ... ON CONFLICT DO NOTHING`) and
never reset or lowered by the application: after creation the database row is authoritative,
and changing a cap is an operator action that needs the user's approval
(`docs/HOSTED_OPERATIONS.md`).

**Operations** (each in its own transaction, on a connection with autocommit on, so that each
`conn.transaction()` block is a real top-level transaction, as in stage D):

- `reserve`: the reservation row and every cap row in one transaction, cap rows updated in
  sorted key order (no deadlock between opposite orders), each by a single conditional
  UPDATE (re-checked after a concurrent transaction under READ COMMITTED). All or nothing: a
  refusal leaves no partial change. The request ID is the primary key, so a repeated ID never
  reserves twice.
- `dispatched`: committed before the request is sent, so a crash afterwards keeps the cost.
- `settle`: exact `Decimal` known usage replaces the reservation; idempotent per request ID.
  Known usage above the reservation is charged exactly (never capped at an estimate).
- `hold`: unknown usage; the reservation stays dispatched at the request ceiling.
- `release`: only a reservation that was never dispatched. A dispatched reservation is never
  released, by timeout or otherwise; only `settle` (an operator's reconciliation) resolves it.

**Events** (`atlas_event`): time, route, event code and amount only. Never the key, the access
code (typed or configured), the database URL, prompts or replies.

This module imports no database driver: `connect` is a callable returning an open psycopg 3
connection with autocommit on (`connector(url)` builds one).
"""

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from atlas.agent import money
from atlas.agent.budget import ReservationRefused

PUBLIC = "public"
JUDGE = "judge"
ROUTES = (PUBLIC, JUDGE)

# DECIDED by the user (DECISIONS.md "T-12 decisions (user, 2026-10-18)", item 3).
HOSTED_DECIDED = {
    "total_usd": Decimal("8.00"),
    "public_pool_usd": Decimal("3.00"),
    "public_daily_usd": Decimal("1.00"),
    "judge_pool_usd": Decimal("5.00"),
    "session_cap_usd": Decimal("0.0648"),  # the decided per-run estimate cap
    "session_requests": 6,
}

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS atlas_cap (
        cap_key text PRIMARY KEY,
        route text NOT NULL,
        cap_usd numeric NOT NULL CHECK (cap_usd >= 0),
        reserved_usd numeric NOT NULL DEFAULT 0 CHECK (reserved_usd >= 0),
        spent_usd numeric NOT NULL DEFAULT 0 CHECK (spent_usd >= 0),
        max_requests integer CHECK (max_requests >= 0),
        requests integer NOT NULL DEFAULT 0 CHECK (requests >= 0),
        created_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS atlas_reservation (
        request_id text PRIMARY KEY,
        route text NOT NULL,
        state text NOT NULL
            CHECK (state IN ('reserved', 'dispatched', 'settled', 'released')),
        amount_usd numeric NOT NULL CHECK (amount_usd > 0),
        actual_usd numeric CHECK (actual_usd >= 0),
        cap_keys text[] NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    """CREATE TABLE IF NOT EXISTS atlas_event (
        id bigserial PRIMARY KEY,
        time timestamptz NOT NULL DEFAULT now(),
        route text NOT NULL,
        event text NOT NULL,
        amount_usd numeric
    )""",
)
LOCK_TIMEOUT = "SET LOCAL lock_timeout = '10s'"


class StoreError(RuntimeError):
    """The store answered something unexpected; treated like an unreachable store."""


def connector(url: str, *, connect_timeout: int = 15) -> Callable:
    """A `connect()` for the given database URL (psycopg 3, autocommit on). The URL is held
    in the closure only; it is never logged or shown."""

    def connect():
        import psycopg  # imported here so the page renders without the driver

        return psycopg.connect(url, autocommit=True, connect_timeout=connect_timeout)

    return connect


def _utc_today() -> date:
    return datetime.now(UTC).date()


def daily_key(day: date) -> str:
    return f"public_daily:{day.isoformat()}"


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def _refusal_code(key: str, row) -> str:
    """The fixed code for the cap row that refused (no amounts or identifiers)."""
    if key.startswith("session:"):
        if row is not None and row[1] is not None and row[0] + 1 > row[1]:
            return "session_requests"
        return "session_budget"
    if key.startswith("public_daily:"):
        return "public_daily"
    return key if key in ROUTES else "cap"


@dataclass(frozen=True)
class CapState:
    cap_usd: Decimal
    reserved_usd: Decimal
    spent_usd: Decimal
    max_requests: int | None
    requests: int

    @property
    def remaining_usd(self) -> Decimal:
        return money.difference(
            self.cap_usd, money.total((self.reserved_usd, self.spent_usd))
        )


class BudgetStore:
    """The store's operations on one database (see the module docstring)."""

    def __init__(self, connect: Callable, *, today: Callable[[], date] = _utc_today):
        self._connect = connect
        self._conn = None
        self._today = today
        self.decided = dict(HOSTED_DECIDED)

    # -- connection ---------------------------------------------------------------------------
    def _connection(self):
        if self._conn is None or getattr(self._conn, "closed", False):
            self._conn = self._connect()
        return self._conn

    def _run(self, fn):
        """Run `fn(conn)`; on any failure the connection is dropped and the error raised."""
        try:
            return fn(self._connection())
        except ReservationRefused:
            raise
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001, S110 - already unusable
                pass

    # -- schema and caps ------------------------------------------------------------------------
    def setup(self) -> None:
        """Create the tables if absent (idempotent; never drops or empties anything)."""

        def go(conn):
            with conn.transaction():
                for statement in SCHEMA:
                    conn.execute(statement)

        self._run(go)

    def _caps_for(self, route: str, session_id: str) -> dict[str, tuple]:
        """cap_key -> (route, cap_usd, max_requests) for one request on `route`."""
        d = self.decided
        session = (route, d["session_cap_usd"], d["session_requests"])
        if route == PUBLIC:
            return {
                PUBLIC: (PUBLIC, d["public_pool_usd"], None),
                daily_key(self._today()): (PUBLIC, d["public_daily_usd"], None),
                session_key(session_id): session,
            }
        if route == JUDGE:
            return {
                JUDGE: (JUDGE, d["judge_pool_usd"], None),
                session_key(session_id): session,
            }
        raise ValueError("unknown route")

    def _ensure(self, conn, caps: dict[str, tuple]) -> None:
        """Create missing cap rows with their decided caps; existing rows are left as they
        are (the database is authoritative). Its own transaction, before any lock is taken."""
        with conn.transaction():
            for key in sorted(caps):
                route, cap, max_requests = caps[key]
                conn.execute(
                    "INSERT INTO atlas_cap (cap_key, route, cap_usd, max_requests) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT (cap_key) DO NOTHING",
                    (key, route, cap, max_requests),
                )

    def cap_state(self, key: str) -> CapState | None:
        def go(conn):
            return conn.execute(
                "SELECT cap_usd, reserved_usd, spent_usd, max_requests, requests "
                "FROM atlas_cap WHERE cap_key = %s",
                (key,),
            ).fetchone()

        row = self._run(go)
        return None if row is None else CapState(*row)

    # -- events ---------------------------------------------------------------------------------
    def log_event(
        self, route: str, event: str, amount_usd: Decimal | None = None
    ) -> None:
        """One diagnostics row: time, route, a fixed event code and an amount. Nothing else
        is accepted, so no key, code, URL, prompt or reply can be written here."""
        if route not in ROUTES or not event.replace("_", "").replace(":", "").isalnum():
            raise ValueError("events take a known route and a fixed event code")

        def go(conn):
            with conn.transaction():
                conn.execute(
                    "INSERT INTO atlas_event (route, event, amount_usd) VALUES (%s, %s, %s)",
                    (route, event, amount_usd),
                )

        self._run(go)

    def log_quietly(self, route: str, event: str, amount_usd=None) -> None:
        try:
            self.log_event(route, event, amount_usd)
        except Exception:  # noqa: BLE001, S110 - diagnostics never decide spending
            pass

    def events(self, limit: int = 100) -> list[tuple]:
        def go(conn):
            return conn.execute(
                "SELECT time, route, event, amount_usd FROM atlas_event "
                "ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()

        return self._run(go)

    # -- sessions -------------------------------------------------------------------------------
    def open_session(self, route: str, ceiling_usd: Decimal) -> "SessionReservations":
        """Create a live session on `route`. Refused (ReservationRefused) if any of its caps
        cannot take even one request at `ceiling_usd`: nothing is reserved by opening."""
        if route not in ROUTES:
            raise ValueError("unknown route")
        session_id = secrets.token_hex(16)
        caps = self._caps_for(route, session_id)

        def go(conn):
            self._ensure(conn, caps)
            rows = conn.execute(
                "SELECT cap_key, cap_usd, reserved_usd, spent_usd, max_requests, requests "
                "FROM atlas_cap WHERE cap_key = ANY(%s)",
                (sorted(caps),),
            ).fetchall()
            return {r[0]: CapState(*r[1:]) for r in rows}

        states = self._run(go)
        if set(states) != set(caps):
            raise StoreError("cap rows missing after creation")
        for key in sorted(caps):
            s = states[key]
            if money.exceeds(ceiling_usd, s.remaining_usd) or (
                s.max_requests is not None and s.requests >= s.max_requests
            ):
                code = _refusal_code(key, (s.requests, s.max_requests))
                self.log_quietly(route, f"session_refused:{code}")
                raise ReservationRefused(code)
        self.log_quietly(route, "session_opened")
        return SessionReservations(self, session_id, route)

    # -- per-request operations -----------------------------------------------------------------
    def reserve(
        self, request_id: str, route: str, session_id: str, amount: Decimal
    ) -> str:
        """Reserve `amount` against every cap of the request in one transaction; returns
        "reserved" or "duplicate:<state>", or raises ReservationRefused(code)."""
        if money.amount_problem(amount) is not None or amount <= 0:
            raise ValueError("amount must be a positive supported Decimal")
        caps = self._caps_for(route, session_id)
        keys = sorted(caps)

        def go(conn):
            self._ensure(conn, caps)  # today's daily row, if the date changed
            refused = None
            with conn.transaction():
                conn.execute(LOCK_TIMEOUT)
                inserted = conn.execute(
                    "INSERT INTO atlas_reservation "
                    "(request_id, route, state, amount_usd, cap_keys) "
                    "VALUES (%s, %s, 'reserved', %s, %s) "
                    "ON CONFLICT (request_id) DO NOTHING RETURNING request_id",
                    (request_id, route, amount, keys),
                ).fetchone()
                if inserted is None:
                    state = conn.execute(
                        "SELECT state FROM atlas_reservation WHERE request_id = %s",
                        (request_id,),
                    ).fetchone()
                    return f"duplicate:{state[0] if state else 'unknown'}"
                for key in keys:
                    updated = conn.execute(
                        "UPDATE atlas_cap SET reserved_usd = reserved_usd + %s, "
                        "requests = requests + 1 WHERE cap_key = %s "
                        "AND reserved_usd + spent_usd + %s <= cap_usd "
                        "AND (max_requests IS NULL OR requests + 1 <= max_requests)",
                        (amount, key, amount),
                    ).rowcount
                    if updated != 1:
                        row = conn.execute(
                            "SELECT requests, max_requests FROM atlas_cap "
                            "WHERE cap_key = %s",
                            (key,),
                        ).fetchone()
                        refused = ReservationRefused(_refusal_code(key, row))
                        raise refused  # rolls back the whole transaction
            return "reserved"

        try:
            result = self._run(go)
        except ReservationRefused as exc:
            self.log_quietly(route, f"refused:{exc.code}", amount)
            raise
        if result == "reserved":
            self.log_quietly(route, "reserved", amount)
        return result

    def _locked(self, conn, request_id: str):
        return conn.execute(
            "SELECT state, amount_usd, cap_keys, route FROM atlas_reservation "
            "WHERE request_id = %s FOR UPDATE",
            (request_id,),
        ).fetchone()

    def dispatched(self, request_id: str) -> None:
        """Commit 'dispatched' before sending. Raises StoreError unless exactly this reserved
        row changed (then nothing may be sent)."""

        def go(conn):
            with conn.transaction():
                return conn.execute(
                    "UPDATE atlas_reservation SET state = 'dispatched', updated_at = now() "
                    "WHERE request_id = %s AND state = 'reserved'",
                    (request_id,),
                ).rowcount

        if self._run(go) != 1:
            raise StoreError("the reservation is not in the reserved state")

    def settle(self, request_id: str, actual: Decimal) -> str:
        """Replace a dispatched reservation with exact known usage. Idempotent: a second
        settle of the same request ID changes nothing ("already-settled")."""
        if money.amount_problem(actual) is not None:
            raise ValueError("actual must be a non-negative supported Decimal")

        def go(conn):
            with conn.transaction():
                conn.execute(LOCK_TIMEOUT)
                row = self._locked(conn, request_id)
                if row is None:
                    return "unknown", None
                state, amount, keys, route = row
                if state == "settled":
                    return "already-settled", route
                if state != "dispatched":
                    return f"invalid-state:{state}", route
                for key in sorted(keys):
                    conn.execute(
                        "UPDATE atlas_cap SET reserved_usd = reserved_usd - %s, "
                        "spent_usd = spent_usd + %s WHERE cap_key = %s",
                        (amount, actual, key),
                    )
                conn.execute(
                    "UPDATE atlas_reservation SET state = 'settled', actual_usd = %s, "
                    "updated_at = now() WHERE request_id = %s",
                    (actual, request_id),
                )
                return "settled", route

        result, route = self._run(go)
        if result == "settled":
            self.log_quietly(route, "settled", actual)
        return result

    def hold(self, request_id: str) -> str:
        """Unknown usage: the dispatched reservation stays held at its ceiling (no change)."""

        def go(conn):
            return conn.execute(
                "SELECT state, route, amount_usd FROM atlas_reservation "
                "WHERE request_id = %s",
                (request_id,),
            ).fetchone()

        row = self._run(go)
        if row is None:
            return "unknown"
        if row[0] == "dispatched":
            self.log_quietly(row[1], "held_unknown_usage", row[2])
            return "held"
        return f"invalid-state:{row[0]}"

    def release(self, request_id: str) -> str:
        """Release a reservation that was never dispatched; a dispatched one is retained."""

        def go(conn):
            with conn.transaction():
                conn.execute(LOCK_TIMEOUT)
                row = self._locked(conn, request_id)
                if row is None:
                    return "unknown", None
                state, amount, keys, route = row
                if state == "dispatched":
                    return "retained-dispatched", route
                if state != "reserved":
                    return f"invalid-state:{state}", route
                for key in sorted(keys):
                    conn.execute(
                        "UPDATE atlas_cap SET reserved_usd = reserved_usd - %s, "
                        "requests = requests - 1 WHERE cap_key = %s",
                        (amount, key),
                    )
                conn.execute(
                    "UPDATE atlas_reservation SET state = 'released', updated_at = now() "
                    "WHERE request_id = %s",
                    (request_id,),
                )
                return "released", route

        result, route = self._run(go)
        if result == "released":
            self.log_quietly(route, "released")
        return result

    def reservation(self, request_id: str):
        def go(conn):
            return conn.execute(
                "SELECT state, amount_usd, actual_usd FROM atlas_reservation "
                "WHERE request_id = %s",
                (request_id,),
            ).fetchone()

        return self._run(go)

    # -- retention ------------------------------------------------------------------------------
    def prune(self, older_than_days: int) -> dict:
        """Delete only rows whose effect is already in the cap totals: settled or released
        reservations and events older than the given age. A reserved or dispatched
        reservation is never deleted, and cap rows (cumulative spending) are never reset or
        deleted (docs/HOSTED_OPERATIONS.md "Retention")."""
        if type(older_than_days) is not int or older_than_days < 1:
            raise ValueError("older_than_days must be a positive integer")

        def go(conn):
            with conn.transaction():
                reservations = conn.execute(
                    "DELETE FROM atlas_reservation WHERE state IN ('settled', 'released') "
                    "AND updated_at < now() - make_interval(days => %s)",
                    (older_than_days,),
                ).rowcount
                events = conn.execute(
                    "DELETE FROM atlas_event WHERE time < now() - make_interval(days => %s)",
                    (older_than_days,),
                ).rowcount
            return {"reservations": reservations, "events": events}

        return self._run(go)


class SessionReservations:
    """One live session's binding of the store, passed to `run_agent(reservations=...)`.

    Before every reservation the kill switch is read again (`enabled()`), so switching it off
    stops a session in progress before its next request. Request IDs are `<session>:a<N>`."""

    def __init__(self, store: BudgetStore, session_id: str, route: str, enabled=None):
        self.store, self.session_id, self.route = store, session_id, route
        self.enabled = enabled

    def request_id(self, attempt: int) -> str:
        return f"{self.session_id}:a{attempt}"

    def reserve(self, attempt: int, amount: Decimal) -> str:
        if self.enabled is not None and self.enabled() is not True:
            raise ReservationRefused("live_disabled")
        request_id = self.request_id(attempt)
        result = self.store.reserve(request_id, self.route, self.session_id, amount)
        if result != "reserved":  # a repeated ID: never send twice
            raise StoreError("duplicate request ID")
        return request_id

    def dispatched(self, request_id: str) -> None:
        self.store.dispatched(request_id)

    def settle(self, request_id: str, known_usd: Decimal) -> None:
        result = self.store.settle(request_id, known_usd)
        if result not in ("settled", "already-settled"):
            raise StoreError("settle did not apply")

    def hold(self, request_id: str) -> None:
        if self.store.hold(request_id) != "held":
            raise StoreError("hold did not apply")

    def release(self, request_id: str) -> None:
        if self.store.release(request_id) != "released":
            raise StoreError("release did not apply")
