"""Pre-run model check for a live run (T-06 slice 4; DECISIONS.md 2026-10-16, decision 4).

One free, authenticated `GET {base_url}models?verbose=true`, immediately before a live run and
never a completion. The run may proceed only if the configured model is listed and its listed
input price, output price and context length equal the configuration exactly (prices compared as
`Decimal`). Anything else aborts, and is never treated as a pass:
- a missing model or a mismatched field;
- a transport error or timeout;
- a non-200 status;
- a body over MAX_BODY_BYTES;
- unparseable JSON (including Python's integer-digit limit and over-deep nesting);
- a missing, malformed or out-of-range field.

**Bounded before anything else (Gate 3 repair pass 1).** Provider data is untrusted. The body is
read incrementally and abandoned past MAX_BODY_BYTES. Every listed price is range-checked from its
`Decimal` tuple (`money.price_problem`: finite, non-negative, no negative zero, at most 1e100 USD
per token, at most 30 decimal places) **before** it is formatted, compared or used in arithmetic,
so a short string such as `"1E+100000"` cannot expand. The context length must be a genuine `int`
from 2 to 10**100. Rejected values are recorded only as their raw text cut to RAW_CHARS
characters. The whole evidence record stays under MAX_EVIDENCE_BYTES.

No retries (`httpx2` sends one request; redirects are not followed), and the configured timeout
applies. The returned evidence is sanitized: it records the URL without the query, the status,
the request ID (if it is a plain identifier that does not contain the key), the model ID, the
listed and expected values, the result, the reason and the mismatches. It never records the key,
any header, or provider text beyond the bounded raw value of a rejected field.

The check itself needs the Gate 3 go-ahead; nothing here runs on import. The configuration is an
explicit parameter: this module reads no decided or default values.
"""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx2

from atlas.agent import money
from atlas.agent.client import MAX_TOKEN_COUNT, safe_identifier
from atlas.agent.nebius import NebiusConfig

PREFLIGHT_ABORT_EXIT = (
    6  # CLI exit code when the pre-run check aborts (nothing else ran)
)
PASS, ABORT = "pass", "abort"
FIELDS = ("price_input_per_token", "price_output_per_token", "context_length_tokens")
MAX_BODY_BYTES = 1024 * 1024  # the archived real listing is 31,781 bytes
MAX_EVIDENCE_BYTES = 16 * 1024
RAW_CHARS = 64  # how much of a rejected raw value the evidence keeps
_TYPE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}", re.ASCII)


class _Abort(Exception):
    """Internal: stop with this fixed reason (and optional bounded detail)."""

    def __init__(self, reason: str, rejected: dict | None = None):
        super().__init__(reason)
        self.reason, self.rejected = reason, rejected


def _raw(value) -> str:
    """A bounded text form of a rejected raw value (never a formatted expansion)."""
    if isinstance(value, str):
        text = value
    elif type(value) is int:
        text = (
            str(value)
            if value.bit_length() < 256
            else f"<int of {value.bit_length()} bits>"
        )
    else:
        text = f"<{type(value).__name__}>"
    return text[:RAW_CHARS]


def _price(name: str, value) -> Decimal:
    """The listed price as a range-checked Decimal; _Abort otherwise. Nothing is formatted or
    compared before the tuple-based range check passes."""
    if value is None:
        raise _Abort(f"missing_field: {name}")
    if type(value) is int:
        if value.bit_length() > 400:  # far above 1e100; never converted
            raise _Abort("price_out_of_range", {"field": name, "raw": _raw(value)})
        price = Decimal(value)
    elif isinstance(value, str) and len(value) <= RAW_CHARS:
        try:
            price = Decimal(value)  # constructing from a short string is bounded
        except InvalidOperation:
            raise _Abort(
                "price_malformed", {"field": name, "raw": _raw(value)}
            ) from None
    else:
        raise _Abort("price_malformed", {"field": name, "raw": _raw(value)})
    if money.price_problem(price) is not None:
        raise _Abort("price_out_of_range", {"field": name, "raw": _raw(value)})
    return price


def _context_length(value) -> int:
    if value is None:
        raise _Abort("missing_field: context_length_tokens")
    if type(value) is not int or not 2 <= value <= MAX_TOKEN_COUNT:
        raise _Abort(
            "context_length_out_of_range",
            {"field": "context_length_tokens", "raw": _raw(value)},
        )
    return value


def _evidence(config: NebiusConfig, url: str, now) -> dict:
    return {
        "check": "pre-run GET /models (T-06 slice 4)",
        "time_utc": now(),
        "method": "GET",
        "url": url,
        "model_id": config.model_id,
        "expected": {
            "price_input_per_token": money.text(config.price_input_per_token),
            "price_output_per_token": money.text(config.price_output_per_token),
            "context_length_tokens": config.context_length_tokens,
        },
        "listed": None,
        "status": None,
        "request_id": None,
        "result": ABORT,
        "reason": None,
        "rejected": None,
        "mismatches": [],
        "note": "sanitized: no key, header or provider text is recorded",
    }


def error_evidence(config: NebiusConfig, error_type, now=None) -> dict:
    """Abort evidence for a pre-run check that raised: only the exception's type name."""
    now = now or (lambda: datetime.now(UTC).isoformat())
    evidence = _evidence(config, config.base_url.rstrip("/") + "/models", now)
    name = getattr(error_type, "__name__", "")
    name = name if isinstance(name, str) and _TYPE_NAME.fullmatch(name) else "Exception"
    evidence["reason"] = f"preflight_error: {name}"
    return evidence


def _read_capped(response) -> bytes:
    """The body, read incrementally; _Abort if it exceeds MAX_BODY_BYTES (declared or actual)."""
    declared = response.headers.get("content-length")
    if declared is not None and (
        not declared.isdigit() or len(declared) > 12 or int(declared) > MAX_BODY_BYTES
    ):
        raise _Abort("response_too_large")
    chunks, size = [], 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > MAX_BODY_BYTES:  # the declared length may understate the real one
            raise _Abort("response_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def run_preflight(
    config: NebiusConfig, api_key: str, *, http_client=None, now=None
) -> dict:
    """Send the one GET and return sanitized evidence; `evidence["result"]` is PASS or ABORT."""
    if not isinstance(config, NebiusConfig):
        raise TypeError("config must be a NebiusConfig")
    config.validate()
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("an API key is required")  # the key itself is never echoed
    now = now or (lambda: datetime.now(UTC).isoformat())
    url = config.base_url.rstrip("/") + "/models"
    evidence = _evidence(config, url, now)

    client = http_client or httpx2.Client(timeout=httpx2.Timeout(config.timeout_s))
    failure, body = None, None
    try:
        with client.stream(
            "GET",
            url,
            params={"verbose": "true"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx2.Timeout(config.timeout_s),
            follow_redirects=False,
        ) as response:
            evidence["status"] = response.status_code
            evidence["request_id"] = safe_identifier(
                response.headers.get("x-request-id"), api_key
            )
            if response.status_code != 200:
                failure = f"http_{response.status_code}"
            else:
                body = _read_capped(response)
    except _Abort as stop:
        failure = stop.reason
    except httpx2.TimeoutException:
        failure = "timeout"
    except httpx2.HTTPError as exc:
        failure = f"transport_error: {type(exc).__name__}"
    finally:
        if http_client is None:
            client.close()
    if failure is not None:  # outside the except blocks: nothing chained or echoed
        evidence["reason"] = failure
        return _bounded(evidence)

    try:
        listed = _listed_values(body, config.model_id)
    except _Abort as stop:
        evidence["reason"], evidence["rejected"] = stop.reason, stop.rejected
        return _bounded(evidence)
    # Every listed value is now range-checked, so formatting it is bounded.
    evidence["listed"] = {name: _text(listed[name]) for name in FIELDS}
    expected = {
        "price_input_per_token": config.price_input_per_token,
        "price_output_per_token": config.price_output_per_token,
        "context_length_tokens": config.context_length_tokens,
    }
    mismatches = [
        {
            "field": name,
            "expected": _text(expected[name]),
            "listed": _text(listed[name]),
        }
        for name in FIELDS
        if listed[name] != expected[name]  # exact: Decimal and int equality
    ]
    if mismatches:
        evidence["mismatches"] = mismatches
        evidence["reason"] = "mismatch: " + ", ".join(m["field"] for m in mismatches)
        return _bounded(evidence)
    evidence["result"] = PASS
    return _bounded(evidence)


def _listed_values(body: bytes, model_id: str) -> dict:
    # ValueError covers bad JSON, bad UTF-8 and Python's integer-digit limit; RecursionError
    # covers over-deep nesting. Either is an abort, never an exception.
    try:
        document = json.loads(body)
    except (ValueError, RecursionError):
        raise _Abort("response_malformed") from None
    models = document.get("data") if isinstance(document, dict) else None
    if not isinstance(models, list):
        raise _Abort("missing_field: data")
    matches = [m for m in models if isinstance(m, dict) and m.get("id") == model_id]
    if len(matches) != 1:
        raise _Abort("model_absent" if not matches else "model_listed_twice")
    model = matches[0]
    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        raise _Abort("missing_field: pricing")
    return {
        "price_input_per_token": _price("price_input_per_token", pricing.get("prompt")),
        "price_output_per_token": _price(
            "price_output_per_token", pricing.get("completion")
        ),
        "context_length_tokens": _context_length(model.get("context_length")),
    }


def _bounded(evidence: dict) -> dict:
    """The evidence, guaranteed under MAX_EVIDENCE_BYTES (a fallback that cannot trigger with
    the bounds above, kept so that a future change cannot write an unbounded record)."""
    if len(json.dumps(evidence).encode("utf-8")) <= MAX_EVIDENCE_BYTES:
        return evidence
    return {
        **{k: evidence[k] for k in ("check", "time_utc", "method", "url", "model_id")},
        "status": evidence["status"] if isinstance(evidence["status"], int) else None,
        "result": ABORT,
        "reason": "evidence_too_large",
        "mismatches": [],
        "listed": None,
        "rejected": None,
        "request_id": None,
        "expected": evidence["expected"],
        "note": "sanitized: no key, header or provider text is recorded",
    }


def _text(value):
    """Fixed-point text for a range-checked Decimal (never 3E-7), the value itself otherwise."""
    return money.text(value) if isinstance(value, Decimal) else value


def summary_lines(evidence: dict) -> list[str]:
    """Human-readable lines for the terminal (sanitized evidence only)."""
    head = (
        f"pre-run check: {evidence['result'].upper()} "
        f"({evidence['model_id']}; status {evidence['status']})"
    )
    lines = [head]
    if evidence["reason"]:
        lines.append(f"  reason: {evidence['reason']}")
    for m in evidence["mismatches"]:
        lines.append(f"  {m['field']}: expected {m['expected']}, listed {m['listed']}")
    return lines
