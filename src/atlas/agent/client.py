"""Model clients (SPEC §11): the interface, the fixture client, and the shared checks for
provider-reported values (T-06 slices 2-3).

A client turns one request into one reply or one classified error. It never retries (the
controller owns retries and the attempt budget). The controller parses the whole reply, and
it also passes reported usage and identifiers through the checks below, whatever the client.
The production client is `nebius.NebiusClient` (offline-verified only); asking for live mode
without explicit authorization is refused, never answered with a fixture or any other fallback.

`FixtureClient` replays a named script of replies and errors. It makes no network access and
reads no key or `.env`; every reply it returns is labelled `live: False` and model ID
`fixture:<script>`, which logs and reports carry through.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

MODE_ENV = "ATLAS_MODEL_MODE"


class ModelError(Exception):
    """A request that produced no usable reply.

    `dispatched`: whether the request may have reached the provider (False only when it was
    refused before sending); a dispatched request's cost stays reserved unless `usage` is
    known. Messages are fixed text chosen here, never provider or SDK text.
    """

    transient = False
    code = "model_error"

    def __init__(
        self,
        message: str = "",
        *,
        code=None,
        dispatched=True,
        usage=None,
        invalid_fields=(),
    ):
        super().__init__(message or self.code)
        if code is not None:
            self.code = code
        self.dispatched = dispatched
        self.usage = usage  # validated counts only (see `sanitize_usage`), or None
        self.invalid_fields = tuple(
            invalid_fields
        )  # names from USAGE_FIELDS, never values


class TransientModelError(ModelError):
    """Worth one retry if the attempt budget allows (timeout, connection, 429, 5xx)."""

    transient = True
    code = "transport_error"


class ModelTimeout(TransientModelError):
    code = "model_timeout"


class LiveModeUnavailable(RuntimeError):
    """Live inference is not implemented or not authorized in this build."""


# -- provider-reported values (T-06 slice 3 repair) ---------------------------------------------
# Everything a provider reports is untrusted: SDK response models are not validated at runtime.
# Only checked values reach accounting, actions or logs; a rejected value is replaced, and only
# the name of the field (from the fixed lists here) is recorded, never the rejected value.

USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens")
FINISH_REASONS = ("stop", "length", "content_filter", "tool_calls", "function_call")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}", re.ASCII)


def sanitize_usage(raw) -> tuple[dict, tuple[str, ...]]:
    """Reported usage reduced to {field: count or None} for every field in USAGE_FIELDS.

    A count is known only if it is a genuine non-negative integer (`int`, not `bool`). A missing
    or null field is unknown (None). Anything else (a boolean, fraction, string, negative or
    non-finite number) is invalid: it becomes None and its field name is returned, so the caller
    can fail closed. A `raw` that is not a mapping or an object with these attributes makes every
    field invalid."""
    usage, invalid = {}, []
    if raw is None:
        return {f: None for f in USAGE_FIELDS}, ()
    if isinstance(raw, dict):
        get = raw.get
    elif isinstance(raw, (str, bytes, int, float, list, tuple)):
        return {f: None for f in USAGE_FIELDS}, USAGE_FIELDS
    else:

        def get(name):
            return getattr(raw, name, None)

    for name in USAGE_FIELDS:
        value = get(name)
        if value is None:
            usage[name] = None
        elif type(value) is int and value >= 0:
            usage[name] = value
        else:
            usage[name] = None
            invalid.append(name)
    return usage, tuple(invalid)


def safe_identifier(value, secret: str | None = None) -> str | None:
    """A provider-reported identifier (request ID, served model) if it is a short plain
    identifier that does not contain `secret`; otherwise None (withheld, not logged)."""
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        return None
    if secret and secret in value:
        return None
    return value


def safe_finish_reason(value) -> str | None:
    """A finish reason from the known set, None if absent, else 'unrecognized'."""
    if value is None:
        return None
    return value if value in FINISH_REASONS else "unrecognized"


@dataclass(frozen=True)
class ModelRequest:
    messages: list[dict]
    params: dict  # e.g. max_completion_tokens; recorded with every attempt


@dataclass
class ModelReply:
    content: str | None
    finish_reason: str | None
    model_id: str
    live: bool
    usage: dict = field(default_factory=dict)
    request_id: str | None = None
    served_model: str | None = None  # the model the provider reports having used
    withheld: tuple[
        str, ...
    ] = ()  # provider fields replaced because they failed validation


class ModelClient(Protocol):
    model_id: str
    live: bool

    def complete(self, request: ModelRequest) -> ModelReply: ...

    # Optional (live clients): `check_request(request)` raises ModelError(dispatched=False)
    # before anything is sent; `ceiling_cost()` returns Decimal USD at both ceilings, and
    # `component_costs(usage)` / `component_ceilings()` return (input, output) Decimal USD,
    # with None for a component whose count is unknown.


_ERRORS = {
    "timeout": ModelTimeout,
    "transport": TransientModelError,
    "rate_limited": TransientModelError,
    "server_error": TransientModelError,
    "rejected": ModelError,  # e.g. HTTP 400: not transient, never retried
}


class FixtureClient:
    """Replays `script` entries in order, one per attempt. An entry is either
    {"content": str | None, "finish_reason": str, "usage": {...}} or {"error": kind}."""

    live = False

    def __init__(self, name: str, script: list[dict]):
        if not name or "/" in name or "\\" in name:
            raise ValueError("fixture script name must be a plain identifier")
        self.name = name
        self.model_id = f"fixture:{name}"
        self._script = list(script)
        self.requests: list[ModelRequest] = []

    @classmethod
    def from_file(cls, path: Path) -> "FixtureClient":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["name"], data["replies"])

    def complete(self, request: ModelRequest) -> ModelReply:
        self.requests.append(request)
        if not self._script:
            raise ModelError("fixture script exhausted")
        entry = self._script.pop(0)
        if "error" in entry:
            raise _ERRORS[entry["error"]](f"fixture error: {entry['error']}")
        return ModelReply(
            content=entry.get("content"),
            finish_reason=entry.get("finish_reason", "stop"),
            model_id=self.model_id,
            live=False,
            usage=dict(entry.get("usage") or {}),
            request_id=entry.get("request_id"),
        )


def require_fixture_mode(env=None) -> None:
    """Refuse anything but fixture mode; never fall back to another mode."""
    mode = (env if env is not None else os.environ).get(MODE_ENV, "fixture")
    if mode != "fixture":
        raise LiveModeUnavailable(
            f"{MODE_ENV}={mode!r}: live inference is not authorized in this build "
            "(T-06 slice 4 needs explicit authorization); no fallback to fixture mode"
        )
