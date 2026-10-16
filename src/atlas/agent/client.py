"""Model clients (SPEC §11). T-06 slice 2: the interface and the fixture client only.

A client turns one request into one reply or one classified error. It never retries (the
controller owns retries and the attempt budget) and never validates (the controller parses the
whole reply). The production Nebius transport is a later slice; asking for live mode here is
refused, never answered with a fixture or any other fallback.

`FixtureClient` replays a named script of replies and errors. It makes no network access and
reads no key or `.env`; every reply it returns is labelled `live: False` and model ID
`fixture:<script>`, which logs and reports carry through.
"""

import json
import os
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

    def __init__(self, message: str = "", *, code=None, dispatched=True, usage=None):
        super().__init__(message or self.code)
        if code is not None:
            self.code = code
        self.dispatched = dispatched
        self.usage = usage


class TransientModelError(ModelError):
    """Worth one retry if the attempt budget allows (timeout, connection, 429, 5xx)."""

    transient = True
    code = "transport_error"


class ModelTimeout(TransientModelError):
    code = "model_timeout"


class LiveModeUnavailable(RuntimeError):
    """Live inference is not implemented or not authorized in this build."""


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


class ModelClient(Protocol):
    model_id: str
    live: bool

    def complete(self, request: ModelRequest) -> ModelReply: ...

    # Optional (live clients): `check_request(request)` raises ModelError(dispatched=False)
    # before anything is sent; `ceiling_cost()` and `usage_cost(usage)` return Decimal USD
    # (None when usage is incomplete).


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
