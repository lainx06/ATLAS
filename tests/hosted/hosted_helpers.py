"""Shared helpers for the hosted-mode tests (T-12): a mocked Token Factory and a recording
in-memory reservations store. No request leaves the process: the production client and the
pre-run check run over an `httpx2.MockTransport`.
"""

import functools
import json
from decimal import Decimal
from pathlib import Path

import httpx2

from atlas.agent import nebius
from atlas.agent import preflight as pf
from atlas.agent.budget import DECIDED_SLICE4, ReservationRefused, SpendLimits

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
S01 = ROOT / "benchmarks" / "t01" / "s01_faulty"
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = BUNDLE / "live6" / "agent-s01_faulty-877f8245a8a2"
LISTING = json.loads(
    (FIXTURES / "nebius_models_verbose.json").read_text(encoding="utf-8")
)
MODEL = "nvidia/nemotron-3-super-120b-a12b"
# Synthetic secret markers: none may ever appear in a page, log, report, event or the bundle.
KEY = "sk-T12SYNTHETICKEYMARKER-0f3a9c"
JUDGE_CODE = "T12-JUDGE-CODE-MARKER-7d41b2"
DB_PASSWORD_MARKER = "T12DBPASSMARKER"
# Live run 6's first three replies (list, read, the new_source revision), then a finish.
LIVE6_REPLIES = [
    (FIXTURES / f"live6_a{n}.txt").read_bytes().decode("utf-8") for n in (1, 2, 3)
]
FINISH = json.dumps({"action": {"tool": "finish", "summary": "Proposed one revision."}})
USAGE = {"prompt_tokens": 4000, "completion_tokens": 600, "total_tokens": 4600}
# 4,000 x 0.0000003 + 600 x 0.0000009
USAGE_USD = Decimal("0.00174")


def completion(content, usage=USAGE, finish="stop"):
    return {
        "id": "cmpl-t12",
        "object": "chat.completion",
        "created": 0,
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": usage,
    }


class Provider:
    """A mock Token Factory: GET /models returns the archived listing; POST
    /chat/completions returns the scripted completions in order (or raises an entry that is
    an exception class)."""

    def __init__(self, completions=(), on_post=None):
        self.completions = list(completions)
        self.requests = []
        self.on_post = on_post

    def __call__(self, request):
        self.requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/models"):
            return httpx2.Response(
                200,
                content=json.dumps(LISTING).encode("utf-8"),
                headers={"content-type": "application/json", "x-request-id": "pf-1"},
            )
        if self.on_post is not None:
            self.on_post(request)
        body = self.completions.pop(0)
        if isinstance(body, type) and issubclass(body, Exception):
            raise body("mock failure", request=request)
        return httpx2.Response(
            200, json=body, headers={"x-request-id": f"req-{len(self.requests)}"}
        )

    def posts(self):
        return [r for r in self.requests if r.method == "POST"]

    def gets(self):
        return [r for r in self.requests if r.method == "GET"]


def live6_provider(**kwargs):
    return Provider([completion(c) for c in [*LIVE6_REPLIES, FINISH]], **kwargs)


_REAL_PREFLIGHT, _REAL_CLIENT = pf.run_preflight, nebius.NebiusClient


def wire(monkeypatch, provider):
    """Route the pre-run check and the production client to the mock provider."""
    http = httpx2.Client(transport=httpx2.MockTransport(provider))
    real_preflight, real_client = _REAL_PREFLIGHT, _REAL_CLIENT
    monkeypatch.setattr(
        pf, "run_preflight", functools.partial(real_preflight, http_client=http)
    )
    monkeypatch.setattr(
        nebius,
        "NebiusClient",
        lambda config, key: real_client(config, key, http_client=http),
    )
    return http


CONFIG_KEYS = (
    "base_url", "model_id", "max_input_tokens", "max_completion_tokens",
    "template_overhead_tokens", "timeout_s", "price_input_per_token",
    "price_output_per_token", "context_length_tokens",
)  # fmt: skip


def decided_config():
    return nebius.NebiusConfig(**{k: DECIDED_SLICE4[k] for k in CONFIG_KEYS})


def decided_limits():
    return SpendLimits(
        authorized_usd=DECIDED_SLICE4["authorized_usd"],
        estimate_cap_usd=DECIDED_SLICE4["estimate_cap_usd"],
    )


def client(provider):
    return nebius.NebiusClient(
        decided_config(),
        KEY,
        http_client=httpx2.Client(transport=httpx2.MockTransport(provider)),
    )


class FakeReservations:
    """An in-memory stand-in for the store binding that records every call, in order."""

    def __init__(self, refuse_at=None, fail=None, provider=None):
        self.calls = []
        self.refuse_at, self.fail = refuse_at, fail or {}
        self.provider = provider

    def _posts(self):
        return len(self.provider.posts()) if self.provider is not None else None

    def _maybe_fail(self, name):
        if name in self.fail:
            raise self.fail[name]("store failure")

    def reserve(self, attempt, amount):
        self.calls.append(("reserve", attempt, amount, self._posts()))
        self._maybe_fail("reserve")
        if self.refuse_at is not None and attempt >= self.refuse_at:
            raise ReservationRefused("public_daily")
        return f"s:a{attempt}"

    def dispatched(self, handle):
        self.calls.append(("dispatched", handle, self._posts()))
        self._maybe_fail("dispatched")

    def settle(self, handle, known):
        self.calls.append(("settle", handle, known, self._posts()))
        self._maybe_fail("settle")

    def hold(self, handle):
        self.calls.append(("hold", handle, self._posts()))

    def release(self, handle):
        self.calls.append(("release", handle, self._posts()))

    def names(self):
        return [c[0] for c in self.calls]


class SpyApprover:
    def __init__(self):
        self.requests = []

    def decide(self, request):
        self.requests.append(request)
        raise AssertionError("no approval may be asked in hosted mode")


def local_original(run):
    """A local-style original (as if run in Docker): the recorded original's files copied,
    reported with the Docker runner, so a local fixture run can be compared."""
    import shutil

    from atlas.agent import controller as ctl
    from atlas.contracts import RunOutcome

    dest = run.run_dir / "original"
    shutil.copytree(LIVE6 / "original", dest)
    outcome = RunOutcome.model_validate_json((dest / "outcome.json").read_text("utf-8"))
    return ctl.OriginalRun(dest, outcome, "docker_isolated", True, {})


class Decline:
    def decide(self, request):
        return None


def local_fixture_run(tmp_path):
    """A local (not hosted) fixture run with one proposal that is declined."""
    from atlas.agent import controller as ctl
    from atlas.agent.client import FixtureClient

    script = [{"content": c} for c in [*LIVE6_REPLIES, FINISH]]
    result = ctl.run_agent(
        S01, tmp_path / "local", FixtureClient("t12-local", script), Decline(),
        original=local_original, env={},
    )  # fmt: skip
    return result.report


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class NonLoopbackDenied(OSError):
    pass


def loopback_only():
    """A context manager: Python networking in this process may reach loopback addresses
    only (Streamlit's in-process event loop and the local test database); anything else
    raises NonLoopbackDenied and is recorded in `.attempts`. An in-process test safeguard,
    not a sandbox."""
    import contextlib
    import socket

    attempts = []

    def host_of(address):
        return address[0] if isinstance(address, tuple) and address else address

    def guard(original):
        def wrapper(self_or_addr, *args, **kwargs):
            address = args[0] if args else kwargs.get("address")
            if isinstance(self_or_addr, socket.socket):
                target = host_of(address)
            else:  # create_connection(address, ...)
                target = host_of(self_or_addr)
            if target not in LOOPBACK:
                attempts.append(str(target))
                raise NonLoopbackDenied(f"non-loopback connection to {target!r} denied")
            return original(self_or_addr, *args, **kwargs)

        return wrapper

    def resolver(original):
        def wrapper(host, *args, **kwargs):
            if host not in LOOPBACK and host is not None:
                attempts.append(str(host))
                raise NonLoopbackDenied(f"resolution of {host!r} denied")
            return original(host, *args, **kwargs)

        return wrapper

    @contextlib.contextmanager
    def manager():
        saved = {
            "connect": socket.socket.connect,
            "connect_ex": socket.socket.connect_ex,
            "create_connection": socket.create_connection,
            "getaddrinfo": socket.getaddrinfo,
        }
        socket.socket.connect = guard(saved["connect"])
        socket.socket.connect_ex = guard(saved["connect_ex"])
        socket.create_connection = guard(saved["create_connection"])
        socket.getaddrinfo = resolver(saved["getaddrinfo"])
        try:
            yield attempts
        finally:
            socket.socket.connect = saved["connect"]
            socket.socket.connect_ex = saved["connect_ex"]
            socket.create_connection = saved["create_connection"]
            socket.getaddrinfo = saved["getaddrinfo"]

    return manager()
