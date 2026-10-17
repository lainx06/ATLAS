"""Pre-run model check for a live run (T-06 slice 4; DECISIONS.md 2026-10-16, decision 4).

One free, authenticated `GET {base_url}models?verbose=true`, immediately before a live run and
never a completion. The run may proceed only if the configured model is listed and its listed
input price, output price and context length equal the configuration exactly (prices compared as
`Decimal`). Anything else aborts, and is never treated as a pass:
- a missing model or a mismatched field;
- a transport error or timeout;
- a non-200 status;
- unparseable JSON;
- a missing or malformed field.

No retries (`httpx2` sends one request; redirects are not followed), and the configured timeout
applies. The returned evidence is sanitized: it records the URL without the query, the status,
the request ID (if it is a plain identifier that does not contain the key), the model ID, the
listed and expected values, the result, the reason and the mismatches. It never records the key,
any header, or provider text.

The check itself needs the Gate 3 go-ahead; nothing here runs on import. The configuration is an
explicit parameter: this module reads no decided or default values.
"""

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import httpx2

from atlas.agent import money
from atlas.agent.client import safe_identifier
from atlas.agent.nebius import NebiusConfig

PREFLIGHT_ABORT_EXIT = (
    6  # CLI exit code when the pre-run check aborts (nothing else ran)
)
PASS, ABORT = "pass", "abort"
FIELDS = ("price_input_per_token", "price_output_per_token", "context_length_tokens")


def _listed_price(value) -> Decimal | None:
    """A listed price as an exact finite Decimal (from a string or an int), else None."""
    if type(value) is int:
        return Decimal(value)
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        price = Decimal(value)
    except InvalidOperation:
        return None
    return price if price.is_finite() else None


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
        "mismatches": [],
        "note": "sanitized: no key, header or provider text is recorded",
    }


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
    failure = None
    try:
        response = client.get(
            url,
            params={"verbose": "true"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx2.Timeout(config.timeout_s),
            follow_redirects=False,
        )
    except httpx2.TimeoutException:
        failure = "timeout"
    except httpx2.HTTPError as exc:
        failure = f"transport_error: {type(exc).__name__}"
    finally:
        if http_client is None:
            client.close()
    if failure is not None:  # outside the except blocks: nothing chained or echoed
        evidence["reason"] = failure
        return evidence

    evidence["status"] = response.status_code
    evidence["request_id"] = safe_identifier(
        response.headers.get("x-request-id"), api_key
    )
    if response.status_code != 200:
        evidence["reason"] = f"http_{response.status_code}"
        return evidence
    try:
        body = json.loads(response.content)
    except ValueError:
        evidence["reason"] = "malformed_json"
        return evidence
    models = body.get("data") if isinstance(body, dict) else None
    if not isinstance(models, list):
        evidence["reason"] = "missing_field: data"
        return evidence
    matches = [
        m for m in models if isinstance(m, dict) and m.get("id") == config.model_id
    ]
    if len(matches) != 1:
        evidence["reason"] = "model_absent" if not matches else "model_listed_twice"
        return evidence
    model = matches[0]
    pricing = model.get("pricing")
    raw = {
        "price_input_per_token": pricing.get("prompt")
        if isinstance(pricing, dict)
        else None,
        "price_output_per_token": pricing.get("completion")
        if isinstance(pricing, dict)
        else None,
        "context_length_tokens": model.get("context_length"),
    }
    listed = {
        "price_input_per_token": _listed_price(raw["price_input_per_token"]),
        "price_output_per_token": _listed_price(raw["price_output_per_token"]),
        "context_length_tokens": raw["context_length_tokens"]
        if type(raw["context_length_tokens"]) is int
        else None,
    }
    missing = [name for name in FIELDS if listed[name] is None]
    evidence["listed"] = {
        name: (None if listed[name] is None else _text(listed[name])) for name in FIELDS
    }
    if missing:
        evidence["reason"] = "missing_field: " + ", ".join(missing)
        return evidence
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
        return evidence
    evidence["result"] = PASS
    return evidence


def _text(value):
    """Fixed-point text for a Decimal (never 3E-7), the value itself otherwise."""
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
