"""T-06 slice 4, Gate 3 implementation (offline): the live entry point and the pre-run check.

No request leaves the process. Every HTTP exchange goes to an `httpx2.MockTransport` handler,
and each CLI call runs under the fixture network guard, so a real connection would fail. The key
is a synthetic marker in a temporary file; the repository `.env` is never read. Docker is faked
with the slice 1 harness. Nothing here is a pre-run call or a live run.
"""

import copy
import functools
import importlib.util
import io
import json
import sys
from decimal import Decimal
from pathlib import Path

import httpx2
import pytest

from atlas import cli
from atlas.agent import budget, nebius
from atlas.agent import controller as ctl

try:  # new at Gate 3; imported defensively so this file also runs at the parent (red run)
    from atlas.agent import preflight
except ImportError:
    preflight = None
from atlas.agent.network import deny_network
from atlas.runner import docker as dr
from atlas.runner import trusted


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name.replace(".py", ""), Path(__file__).with_name(name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("test_agent_slice3.py")
KEY, FINISH, PATCH, S01 = S.KEY, S.FINISH, S.PATCH, S.S01
LISTING = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "nebius_models_verbose.json").read_text(
        encoding="utf-8"
    )
)
MODEL = "nvidia/nemotron-3-super-120b-a12b"
MAX_EVIDENCE = 16 * 1024  # bytes (Gate 3 repair pass 1)
DECIDED = getattr(budget, "DECIDED_SLICE4", {})


# =============================================================================================
# Harness
# =============================================================================================


class Provider:
    """A mock Token Factory: GET /models returns `listing` (or an injected failure); POST
    /chat/completions returns the scripted completions in order."""

    def __init__(self, listing=None, completions=(), models_status=200, models_raw=None,
                 models_error=None):  # fmt: skip
        self.listing = copy.deepcopy(LISTING if listing is None else listing)
        self.completions = list(completions)
        self.models_status, self.models_raw = models_status, models_raw
        self.models_error = models_error
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if request.method == "GET" and request.url.path.endswith("/models"):
            if self.models_error is not None:
                raise self.models_error("mock failure " + KEY, request=request)
            content = (
                self.models_raw
                if self.models_raw is not None
                else json.dumps(self.listing).encode("utf-8")
            )
            return httpx2.Response(
                self.models_status, content=content,
                headers={"content-type": "application/json", "x-request-id": "pf-1"},
            )  # fmt: skip
        body = self.completions.pop(0)
        return httpx2.Response(
            200, json=body, headers={"x-request-id": f"req-{len(self.requests)}"}
        )

    def gets(self):
        return [r for r in self.requests if r.method == "GET"]

    def posts(self):
        return [r for r in self.requests if r.method == "POST"]


def model_entry(listing):
    return next(m for m in listing["data"] if m["id"] == MODEL)


class Tripwire(Exception):
    pass


def tripwire(name):
    def trip(*args, **kwargs):
        raise Tripwire(f"{name} was reached")

    return trip


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.env"
    path.write_text(f"NEBIUS_API_KEY={KEY}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "LIVE_ENV_FILE", path)
    return path


@pytest.fixture
def no_side_effects(monkeypatch):
    """Everything after the refusal checks fails the test if reached."""
    monkeypatch.setattr(nebius, "load_api_key", tripwire("key read"))
    monkeypatch.setattr(nebius, "NebiusClient", tripwire("client built"))
    monkeypatch.setattr(preflight, "run_preflight", tripwire("pre-run check"))
    monkeypatch.setattr(ctl, "run_agent", tripwire("run_agent"))
    monkeypatch.setattr(dr, "probe", tripwire("Docker probe"))
    monkeypatch.setattr(dr, "_docker", tripwire("Docker CLI"))


def wire(monkeypatch, provider):
    """Route the pre-run check and the production client to the mock provider."""
    http = httpx2.Client(transport=httpx2.MockTransport(provider))
    real_preflight, real_client = preflight.run_preflight, nebius.NebiusClient
    monkeypatch.setattr(
        preflight, "run_preflight", functools.partial(real_preflight, http_client=http)
    )
    monkeypatch.setattr(
        nebius,
        "NebiusClient",
        lambda config, key: real_client(config, key, http_client=http),
    )


def run_cli(tmp_path, monkeypatch, argv, *, mode="live", answers=()):
    out, err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setattr(sys, "stdin", S.FakeStdin(list(answers), out=out))
    if mode is None:
        monkeypatch.delenv("ATLAS_MODEL_MODE", raising=False)
    else:
        monkeypatch.setenv("ATLAS_MODEL_MODE", mode)
    with deny_network():
        code = cli.main(
            ["audit", str(S01), "--runs-dir", str(tmp_path / "runs"), *argv]
        )
    return code, out.getvalue(), err.getvalue()


LIVE = ["--mode", "agent", "--live", "--authorize-spend-usd", "0.51"]


# =============================================================================================
# Refusals 1-4: exit 2 before any run directory, Docker call, key read, client or request
# =============================================================================================


@pytest.mark.parametrize(
    ("argv", "mode"),
    [
        (["--mode", "audit", "--live", "--authorize-spend-usd", "0.51"], "live"),
        (["--live", "--authorize-spend-usd", "0.51"], "live"),  # default mode is audit
        ([*LIVE, "--fixture-script", "script.json"], "live"),
        (["--mode", "agent", "--authorize-spend-usd", "0.51"], "live"),  # amount without --live
        (LIVE, None),
        (LIVE, "fixture"),
        (LIVE, "LIVE"),
    ],
    ids=["mode-audit", "mode-default", "with-fixture-script", "amount-without-live",
         "mode-unset", "mode-fixture", "mode-uppercase"],
)  # fmt: skip
def test_flag_and_mode_refusals(tmp_path, monkeypatch, no_side_effects, argv, mode):
    code, out, err = run_cli(tmp_path, monkeypatch, argv, mode=mode)
    assert code == cli.REFUSED_EXIT == 2
    assert "Nothing was run." in err
    assert not (tmp_path / "runs").exists()
    assert KEY not in out + err


@pytest.mark.parametrize(
    "amount",
    [
        None,
        "0.50",
        "0.52",
        "abc",
        "NaN",
        "Infinity",
        "-0.51",
        "",
        "5.1e-1x",
        # Gate 3 P2-2: distinct from 0.51 as Decimals, equal to it as floats
        "0.51000000000000001",
        "0.50999999999999999",
    ],
)
def test_amount_refusals(tmp_path, monkeypatch, no_side_effects, amount):
    argv = ["--mode", "agent", "--live"]
    if amount is not None:
        argv += ["--authorize-spend-usd", amount]
    code, _out, err = run_cli(tmp_path, monkeypatch, argv)
    assert code == 2 and not (tmp_path / "runs").exists()
    assert "the decided authorization 0.51 USD" in err
    assert ("missing" if amount is None else repr(amount)) in err


@pytest.mark.parametrize(
    ("field", "value"),
    [("price_output_per_token", Decimal("0.000002")), ("estimate_cap_usd", Decimal("0.0107"))],
    ids=["worst-case-above-authorization", "cap-below-one-request"],
)  # fmt: skip
def test_spending_limit_refusals(tmp_path, monkeypatch, no_side_effects, field, value):
    monkeypatch.setitem(budget.DECIDED_SLICE4, field, value)
    code, _out, err = run_cli(tmp_path, monkeypatch, LIVE)
    assert code == 2 and "spending limits refused" in err
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("amount", ["0.51", "0.510", " 0.51"])
def test_equal_amounts_pass_the_refusal_checks(tmp_path, monkeypatch, key_file, amount):
    """Accepted amounts reach the pre-run check; an absent model then stops the run there."""
    listing = copy.deepcopy(LISTING)
    listing["data"] = [m for m in listing["data"] if m["id"] != MODEL]
    provider = Provider(listing)
    wire(monkeypatch, provider)
    monkeypatch.setattr(ctl, "run_agent", tripwire("run_agent"))
    argv = ["--mode", "agent", "--live", "--authorize-spend-usd", amount]
    code, _, _ = run_cli(tmp_path, monkeypatch, argv)
    assert code == cli.PREFLIGHT_ABORT_EXIT == preflight.PREFLIGHT_ABORT_EXIT == 6
    assert len(provider.gets()) == 1 and provider.posts() == []


def test_fixture_mode_is_unchanged(tmp_path, monkeypatch):
    script = tmp_path / "script.json"
    script.write_text(json.dumps({"name": "f", "replies": [{"content": FINISH}]}))
    monkeypatch.setattr(ctl, "docker_original", S.host_fixture_original)
    code, out, _ = run_cli(
        tmp_path, monkeypatch, ["--mode", "agent", "--fixture-script", str(script)],
        mode="fixture",
    )  # fmt: skip
    assert code == 0 and "NON-LIVE agent run" in out and "terminal state: REPORT" in out


# =============================================================================================
# The pre-run check through the CLI: every abort sends no completion and exits 6
# =============================================================================================


def _absent(listing):
    listing["data"] = [m for m in listing["data"] if m["id"] != MODEL]


def _set(path, value):
    def change(listing):
        target = model_entry(listing)
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return change


def _drop(path):
    def change(listing):
        target = model_entry(listing)
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return change


ABORTS = {
    "model-absent": ({"change": _absent}, "model_absent"),
    "input-price": ({"change": _set(("pricing", "prompt"), "0.0000004")}, "mismatch"),
    "output-price": ({"change": _set(("pricing", "completion"), "0.000001")}, "mismatch"),
    "context-length": ({"change": _set(("context_length",), 131072)}, "mismatch"),
    "status-503": ({"status": 503}, "http_503"),
    "status-401": ({"status": 401}, "http_401"),
    "timeout": ({"error": httpx2.ReadTimeout}, "timeout"),
    "connection": ({"error": httpx2.ConnectError}, "transport_error"),
    "malformed-json": ({"raw": b"{not json"}, "response_malformed"),
    "missing-data": ({"raw": b'{"object": "list"}'}, "missing_field: data"),
    "missing-price": ({"change": _drop(("pricing", "completion"))}, "missing_field"),
    "missing-context": ({"change": _drop(("context_length",))}, "missing_field"),
    "float-context": (
        {"change": _set(("context_length",), 262144.0)},
        "context_length_out_of_range",
    ),
}  # fmt: skip


@pytest.mark.parametrize("case", sorted(ABORTS))
def test_every_preflight_abort_exits_6_without_a_completion(
    tmp_path, monkeypatch, key_file, case
):
    spec, reason = ABORTS[case]
    listing = copy.deepcopy(LISTING)
    if "change" in spec:
        spec["change"](listing)
    provider = Provider(
        listing,
        models_status=spec.get("status", 200),
        models_raw=spec.get("raw"),
        models_error=spec.get("error"),
    )
    wire(monkeypatch, provider)
    monkeypatch.setattr(ctl, "run_agent", tripwire("run_agent"))
    monkeypatch.setattr(dr, "probe", tripwire("Docker probe"))
    code, out, err = run_cli(tmp_path, monkeypatch, LIVE)
    assert code == 6
    assert (
        len(provider.gets()) == 1 and provider.posts() == []
    )  # no retry, no completion
    (path,) = (tmp_path / "runs").glob("preflight-*.json")
    assert not list((tmp_path / "runs").glob("agent-*"))  # no run directory
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["result"] == "abort" and evidence["reason"].startswith(reason)
    text = out + err + path.read_text(encoding="utf-8")
    assert KEY not in text and "mock failure" not in text
    assert "authorization" not in path.read_text(encoding="utf-8").lower()
    assert len(path.read_bytes()) <= MAX_EVIDENCE  # Gate 3 P2-1: bounded evidence


@pytest.mark.parametrize(
    ("field", "change", "listed"),
    [
        ("price_input_per_token", _set(("pricing", "prompt"), "0.0000004"), "0.0000004"),
        ("price_output_per_token", _set(("pricing", "completion"), "0.000001"), "0.000001"),
        ("context_length_tokens", _set(("context_length",), 131072), 131072),
    ],
)  # fmt: skip
def test_a_mismatch_names_the_field_with_expected_and_listed(field, change, listed):
    listing = copy.deepcopy(LISTING)
    change(listing)
    provider = Provider(listing)
    evidence = preflight_once(provider)
    (mismatch,) = evidence["mismatches"]
    assert mismatch["field"] == field and mismatch["listed"] == listed
    expected = {
        "price_input_per_token": "0.0000003",
        "price_output_per_token": "0.0000009",
        "context_length_tokens": 262144,
    }[field]
    assert mismatch["expected"] == expected


def decided_config():
    return nebius.NebiusConfig(**{k: DECIDED[k] for k in cli.CONFIG_KEYS})


def preflight_once(provider):
    http = httpx2.Client(transport=httpx2.MockTransport(provider))
    with deny_network():
        return preflight.run_preflight(decided_config(), KEY, http_client=http)


def test_the_preflight_request_shape():
    provider = Provider()
    evidence = preflight_once(provider)
    assert evidence["result"] == "pass" and evidence["mismatches"] == []
    (request,) = provider.requests
    assert request.method == "GET" and request.content == b""
    assert (
        str(request.url) == "https://api.tokenfactory.nebius.com/v1/models?verbose=true"
    )
    assert request.headers["authorization"] == f"Bearer {KEY}"  # outgoing only
    assert evidence["request_id"] == "pf-1"
    assert evidence["listed"] == {
        "price_input_per_token": "0.0000003",
        "price_output_per_token": "0.0000009",
        "context_length_tokens": 262144,
    }
    assert KEY not in json.dumps(evidence)


def test_equal_prices_in_another_notation_pass():
    listing = copy.deepcopy(LISTING)
    model_entry(listing)["pricing"]["prompt"] = "3E-7"  # the same Decimal value
    assert preflight_once(Provider(listing))["result"] == "pass"


def test_a_key_shaped_request_id_is_withheld():
    class Echo(Provider):
        def __call__(self, request):
            response = super().__call__(request)
            response.headers["x-request-id"] = KEY
            return response

    evidence = preflight_once(Echo())
    assert evidence["request_id"] is None and KEY not in json.dumps(evidence)


# =============================================================================================
# Gate 3 repair pass 1 (runs/g3v/review.md): bounded provider values, a raised pre-run check
# =============================================================================================

MARKER = "synthetic-marker-7f3a"


@pytest.mark.parametrize("error", [RuntimeError, OSError, ValueError])
def test_a_raised_preflight_is_an_abort(tmp_path, monkeypatch, key_file, error):
    """P2-3: an exception from the check exits 6 with only its type name; nothing follows."""
    provider = Provider(completions=[S.ok_body(FINISH, None, model=MODEL)])

    def raising(*args, **kwargs):
        raise error(MARKER + " " + KEY)

    monkeypatch.setattr(preflight, "run_preflight", raising)
    monkeypatch.setattr(nebius, "NebiusClient", tripwire("client built"))
    monkeypatch.setattr(ctl, "run_agent", tripwire("run_agent"))
    monkeypatch.setattr(dr, "probe", tripwire("Docker probe"))
    monkeypatch.setattr(dr, "_docker", tripwire("Docker CLI"))
    code, out, err = run_cli(tmp_path, monkeypatch, LIVE)
    assert code == 6 and provider.requests == []  # no completion (nor any request)
    (path,) = (tmp_path / "runs").glob("preflight-*.json")
    assert not list((tmp_path / "runs").glob("agent-*"))
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["result"] == "abort"
    assert evidence["reason"] == f"preflight_error: {error.__name__}"
    text = out + err + path.read_text(encoding="utf-8")
    assert MARKER not in text and KEY not in text
    assert len(path.read_bytes()) <= MAX_EVIDENCE


def _over_mib():
    body = json.dumps(LISTING).encode("utf-8")
    return body + b" " * (
        1024 * 1024 + 1 - len(body)
    )  # valid JSON, one byte over 1 MiB


BOUNDED = {
    # prices (the prompt field unless stated)
    "price-1E+100000": ({"change": _set(("pricing", "prompt"), "1E+100000")}, "price_out_of_range"),
    "price-1E-100000": ({"change": _set(("pricing", "prompt"), "1E-100000")}, "price_out_of_range"),
    "price-1e101": ({"change": _set(("pricing", "prompt"), "1e101")}, "price_out_of_range"),
    "price-1E+31": ({"change": _set(("pricing", "prompt"), "1E+31")}, "mismatch"),
    "price-minus-zero": ({"change": _set(("pricing", "prompt"), "-0")}, "price_out_of_range"),
    "price-negative": ({"change": _set(("pricing", "completion"), "-1E-7")}, "price_out_of_range"),
    "price-64-digits": ({"change": _set(("pricing", "prompt"), "9" * 64)}, "mismatch"),
    "price-65-chars": ({"change": _set(("pricing", "prompt"), "9" * 65)}, "price_malformed"),
    "price-31-decimals": (
        {"change": _set(("pricing", "prompt"), "0.0000003" + "0" * 24)},
        "price_out_of_range",
    ),
    "price-huge-int": ({"change": _set(("pricing", "completion"), 10**200)}, "price_out_of_range"),
    "price-NaN": ({"change": _set(("pricing", "prompt"), "NaN")}, "price_out_of_range"),
    # context length
    "context-1e100+1": ({"change": _set(("context_length",), 10**100 + 1)}, "context_length_out_of_range"),
    "context-1": ({"change": _set(("context_length",), 1)}, "context_length_out_of_range"),
    "context-negative": ({"change": _set(("context_length",), -262144)}, "context_length_out_of_range"),
    "context-bool": ({"change": _set(("context_length",), True)}, "context_length_out_of_range"),
    # bodies
    "context-5000-digits": (
        {"raw": b'{"data": [{"id": "' + MODEL.encode() + b'", "context_length": '
                + b"9" * 5000 + b"}]}"},
        "response_malformed",
    ),
    "body-over-1MiB": ({"raw": None, "body": "over"}, "response_too_large"),
    "body-understated-length": ({"raw": None, "body": "understated"}, "response_too_large"),
    "body-nested-100000": ({"raw": b"[" * 100_000 + b"]" * 100_000}, "response_malformed"),
}  # fmt: skip


class SizedProvider(Provider):
    """A provider whose /models body is over 1 MiB, optionally with an understated length."""

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    def __call__(self, request):
        self.requests.append(request)
        body = _over_mib()
        headers = {"content-type": "application/json"}
        if self.mode == "understated":
            headers["content-length"] = "100"
        return httpx2.Response(200, content=body, headers=headers)


@pytest.mark.parametrize("case", sorted(BOUNDED))
def test_listed_values_and_bodies_are_bounded(tmp_path, monkeypatch, key_file, case):
    """P2-1: out-of-range or oversized provider data aborts with a fixed code and bounded
    evidence, before any expansion; in-range values still reach the normal comparison."""
    spec, reason = BOUNDED[case]
    if "body" in spec:
        provider = SizedProvider(spec["body"])
    else:
        listing = copy.deepcopy(LISTING)
        if "change" in spec:
            spec["change"](listing)
        provider = Provider(listing, models_raw=spec.get("raw"))
    wire(monkeypatch, provider)
    monkeypatch.setattr(ctl, "run_agent", tripwire("run_agent"))
    monkeypatch.setattr(dr, "probe", tripwire("Docker probe"))
    code, out, err = run_cli(tmp_path, monkeypatch, LIVE)
    assert code == 6
    assert len(provider.gets()) == 1 and provider.posts() == []
    (path,) = (tmp_path / "runs").glob("preflight-*.json")
    raw = path.read_bytes()
    assert len(raw) <= MAX_EVIDENCE and len(out + err) <= MAX_EVIDENCE
    evidence = json.loads(raw)
    assert evidence["result"] == "abort" and evidence["reason"].startswith(reason)
    if evidence["rejected"] is not None:
        assert len(evidence["rejected"]["raw"]) <= 64
    assert KEY not in out + err + raw.decode("utf-8")


def test_the_archived_real_listing_still_passes():
    """Control: the real listing's shape (read-only, if present) still passes."""
    real = Path(__file__).parents[2] / "runs/nebius_smoke/models-verbose-20261014.json"
    if not real.is_file():
        pytest.skip("archived listing absent; the synthetic control covers the shape")
    evidence = preflight_once(Provider(models_raw=real.read_bytes()))
    assert evidence["result"] == "pass" and evidence["mismatches"] == []
    assert len(json.dumps(evidence).encode("utf-8")) <= MAX_EVIDENCE


def test_the_synthetic_listing_still_passes_within_the_bound():
    evidence = preflight_once(Provider())
    assert evidence["result"] == "pass"
    assert len(json.dumps(evidence).encode("utf-8")) <= MAX_EVIDENCE


# =============================================================================================
# The happy path through the CLI (mock provider, fake Docker, typed approvals)
# =============================================================================================


@pytest.fixture(scope="module")
def evidence_frames(tmp_path_factory):
    base = tmp_path_factory.mktemp("frames")
    out = {}
    for name, project in (("faulty", S01), ("clean", S.S02)):
        run = base / name
        run.mkdir()
        assert (
            trusted.run_trusted_fixture(project, "evaluate.py", run)["returncode"] == 0
        )
        out[name] = S.H.collected(run, base / f"{name}-out")
    return out


def test_the_live_path_end_to_end(tmp_path, monkeypatch, key_file, evidence_frames):
    usage = {"prompt_tokens": 3000, "completion_tokens": 500, "total_tokens": 3500}
    provider = Provider(
        completions=[S.ok_body(PATCH, usage, model=MODEL), S.ok_body(FINISH, usage, model=MODEL)]
    )  # fmt: skip
    wire(monkeypatch, provider)
    S.fake_docker(monkeypatch, [evidence_frames["faulty"], evidence_frames["clean"]])
    monkeypatch.setattr(trusted, "run_trusted_fixture", tripwire("host runner"))
    monkeypatch.setattr("atlas.audit.run_trusted_fixture", tripwire("host runner"))
    code, out, err = run_cli(
        tmp_path, monkeypatch, LIVE, answers=["<prefix>", "<prefix>"]
    )
    assert code == 0, out + err
    assert "pre-run check: PASS" in out and "LIVE agent run" in out
    assert out.count("APPROVAL REQUIRED") == 2
    assert len(provider.gets()) == 1 and 1 <= len(provider.posts()) <= 6
    assert provider.requests[0].method == "GET"  # the check comes first
    for post in provider.posts():
        body = json.loads(post.content)
        assert sorted(body) == ["max_completion_tokens", "messages", "model", "n"]
        assert (body["model"], body["max_completion_tokens"], body["n"]) == (
            MODEL,
            8000,
            1,
        )
    (run_dir,) = (tmp_path / "runs").glob("agent-*")
    report = json.loads((run_dir / "agent_report.json").read_text(encoding="utf-8"))
    assert report["live"] is True and report["mode"] == "live"
    assert report["banner"].startswith("LIVE RUN")
    spending = report["spending"]
    assert (spending["authorized_usd"], spending["estimate_cap_usd"]) == (
        "0.51",
        "0.0648",
    )
    assert spending["provider_worst_case_run_usd"] == "0.5006592"
    assert spending["max_attempts"] == 6
    assert report["preflight"]["result"] == "pass"
    assert report["comparison"]["comparison_basis"].startswith(
        "Original and candidates"
    )
    saved = json.loads((run_dir / "preflight.json").read_text(encoding="utf-8"))
    assert saved == report["preflight"]
    every = out + err + "".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in run_dir.rglob("*") if p.is_file() and p.suffix in (".json", ".jsonl")
    )  # fmt: skip
    assert KEY not in every


# =============================================================================================
# The decided constant and the standalone script
# =============================================================================================


def test_only_the_cli_and_the_script_read_the_decided_constant():
    for module in ("controller.py", "nebius.py", "client.py", "preflight.py"):
        source = (Path(ctl.__file__).parent / module).read_text(encoding="utf-8")
        assert "DECIDED_SLICE4" not in source, module
    signature = __import__("inspect").signature(ctl.run_agent).parameters
    assert signature["spend"].default is None and signature["preflight"].default is None
    assert DECIDED["timeout_s"] == 60.0 and budget.DECIDED_SLICE4_PROPOSED == ()


def _script():
    path = Path(__file__).parents[2] / "scripts" / "live_preflight.py"
    spec = importlib.util.spec_from_file_location("live_preflight", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_script_dry_run_sends_nothing_and_reads_no_key(
    monkeypatch, capsys, tmp_path
):
    script = _script()
    monkeypatch.setattr(script, "load_api_key", tripwire("key read"))
    provider = Provider()
    http = httpx2.Client(transport=httpx2.MockTransport(provider))
    with deny_network():
        code = script.main([], env_file=tmp_path / "absent.env", evidence_dir=tmp_path,
                           http_client=http)  # fmt: skip
    out = capsys.readouterr().out
    assert code == 0 and provider.requests == [] and "DRY RUN" in out
    assert "GET https://api.tokenfactory.nebius.com/v1/models?verbose=true" in out
    assert not list(tmp_path.glob("preflight-*.json"))


@pytest.mark.parametrize(("listing_change", "code"), [(None, 0), (_absent, 6)])
def test_the_script_execute_path_with_a_mock(tmp_path, capsys, listing_change, code):
    listing = copy.deepcopy(LISTING)
    if listing_change:
        listing_change(listing)
    provider = Provider(listing)
    env = tmp_path / "synthetic.env"
    env.write_text(f"NEBIUS_API_KEY={KEY}\n", encoding="utf-8")
    script = _script()
    with deny_network():
        result = script.main(["--execute"], env_file=env, evidence_dir=tmp_path / "ev",
                             http_client=httpx2.Client(transport=httpx2.MockTransport(provider)))  # fmt: skip
    assert result == code and len(provider.requests) == 1 and provider.posts() == []
    (path,) = (tmp_path / "ev").glob("preflight-*.json")
    assert KEY not in path.read_text(encoding="utf-8") + capsys.readouterr().out
