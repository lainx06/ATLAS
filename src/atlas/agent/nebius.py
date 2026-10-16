"""Production Nebius Token Factory client (SPEC §11; T-06 slice 3). Offline-verified only.

This client has never sent a real request: it is tested with a mocked HTTP transport. A live
run (T-06 slice 4) needs separate, explicit authorization, reviewed ceilings and a model ID
confirmed by the authenticated `GET /models`.

What it does with one request:

- **No hidden retries.** The SDK's retries are disabled (`max_retries=0`); the controller owns
  the single retry per transient call and the six-attempt limit.
- **Bounded.** Every value in `NebiusConfig` is required: there are no built-in ceilings,
  timeouts or prices. Before sending, `check_request` refuses a prompt whose conservative token
  bound exceeds `max_input_tokens` (refused requests are never dispatched). The bound assumes
  that no token covers less than one UTF-8 byte of message text, plus the configured
  `template_overhead_tokens` per message for the chat template; that assumption is unverified
  for this tokenizer. After a reply, usage above either ceiling is an error (fail closed),
  charged at the reported usage.
- **Application-validated output.** The prompt asks for JSON; no `response_format`, tools or
  streaming are sent, and nothing on the provider side constrains the format. The controller
  validates the finish reason and the whole reply before any action.
- **No credential exposure.** The key is passed to the SDK only. Errors are classified by
  exception type and HTTP status only: provider and SDK messages (which can echo request text)
  are never used, and the SDK exception is not chained to the error raised here.
- **Conservative cost accounting.** `ceiling_cost()` is the cost of a request at both
  ceilings; `usage_cost()` is None when usage is incomplete, so the caller keeps the ceiling
  reserved for a dispatched request whose usage is unknown. Prices are listed prices from
  configuration; nothing here authorizes spending.
"""

from dataclasses import dataclass
from decimal import Decimal

import httpx2
import openai

from atlas.agent.client import (
    ModelError,
    ModelReply,
    ModelRequest,
    ModelTimeout,
    TransientModelError,
)

KEY_ENV = "NEBIUS_API_KEY"


@dataclass(frozen=True)
class NebiusConfig:
    """Every field is required; the values for a live run are a lead decision (slice 4)."""

    base_url: str
    model_id: str
    max_input_tokens: int
    max_completion_tokens: int
    template_overhead_tokens: int  # per message, for the conservative input bound
    timeout_s: float
    price_input_per_token: Decimal
    price_output_per_token: Decimal

    def __post_init__(self):
        for name in (
            "max_input_tokens",
            "max_completion_tokens",
            "template_overhead_tokens",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if not (isinstance(self.timeout_s, (int, float)) and self.timeout_s > 0):
            raise ValueError("timeout_s must be positive")
        for name in ("price_input_per_token", "price_output_per_token"):
            if not isinstance(getattr(self, name), Decimal):
                raise TypeError(f"{name} must be a Decimal")


class NebiusClient:
    live = True

    def __init__(self, config: NebiusConfig, api_key: str, *, http_client=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("an API key is required")  # the key itself is never echoed
        self.config = config
        self.model_id = config.model_id
        self._sdk = openai.OpenAI(
            api_key=api_key,
            base_url=config.base_url,
            max_retries=0,
            timeout=httpx2.Timeout(config.timeout_s),
            http_client=http_client,
        )

    def __repr__(self) -> str:
        return f"NebiusClient(model_id={self.model_id!r})"

    # -- bounds and cost ----------------------------------------------------------------------
    def input_bound(self, request: ModelRequest) -> int:
        """A conservative upper bound on prompt tokens (see the module docstring)."""
        total = 0
        for message in request.messages:
            content = message.get("content")
            text = content if isinstance(content, str) else ""
            total += len(text.encode("utf-8")) + self.config.template_overhead_tokens
        return total

    def check_request(self, request: ModelRequest) -> None:
        bound = self.input_bound(request)
        if bound > self.config.max_input_tokens:
            raise ModelError(
                "prompt exceeds the input ceiling; not sent",
                code="input_over_ceiling",
                dispatched=False,
            )

    def ceiling_cost(self) -> Decimal:
        c = self.config
        return (
            c.max_input_tokens * c.price_input_per_token
            + c.max_completion_tokens * c.price_output_per_token
        )

    def usage_cost(self, usage: dict) -> Decimal | None:
        prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        if not all(
            isinstance(v, int) and not isinstance(v, bool) for v in (prompt, completion)
        ):
            return None
        c = self.config
        return prompt * c.price_input_per_token + completion * c.price_output_per_token

    # -- the request --------------------------------------------------------------------------
    def complete(self, request: ModelRequest) -> ModelReply:
        self.check_request(request)
        failure = None
        try:
            raw = self._sdk.chat.completions.with_raw_response.create(
                model=self.config.model_id,
                messages=request.messages,
                max_completion_tokens=self.config.max_completion_tokens,
                n=1,
            )
            data = raw.parse()
            request_id = raw.headers.get("x-request-id")
        except openai.APITimeoutError:
            failure = ModelTimeout("request timed out")
        except openai.APIConnectionError:
            failure = TransientModelError("connection failed")  # it may have been sent
        except openai.RateLimitError:
            failure = TransientModelError("rate limited", code="rate_limited")
        except openai.InternalServerError as exc:
            failure = TransientModelError(
                "server error", code=f"server_error_{_status(exc)}"
            )
        except openai.APIStatusError as exc:
            failure = ModelError("request rejected", code=f"http_{_status(exc)}")
        except openai.OpenAIError as exc:
            failure = ModelError("client error", code=f"client_{type(exc).__name__}")
        if failure is not None:
            # Raised outside the except blocks: no chained SDK exception, request or headers.
            raise failure
        return self._reply(data, request_id)

    def _reply(self, data, request_id) -> ModelReply:
        usage = {}
        if getattr(data, "usage", None) is not None:
            u = data.usage
            usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", None),
                "completion_tokens": getattr(u, "completion_tokens", None),
                "total_tokens": getattr(u, "total_tokens", None),
            }
        choices = getattr(data, "choices", None) or []
        if len(choices) != 1:
            raise ModelError(
                "unexpected number of choices", code="bad_response", usage=usage
            )
        prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        over = (isinstance(prompt, int) and prompt > self.config.max_input_tokens) or (
            isinstance(completion, int)
            and completion > self.config.max_completion_tokens
        )
        if over:
            raise ModelError(
                "reported usage exceeds a configured ceiling",
                code="usage_over_ceiling",
                usage=usage,
            )
        choice = choices[0]
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        return ModelReply(
            content=content if isinstance(content, str) else None,
            finish_reason=getattr(choice, "finish_reason", None),
            model_id=self.config.model_id,
            live=True,
            usage=usage,
            request_id=request_id if isinstance(request_id, str) else None,
            served_model=getattr(data, "model", None),
        )


def _status(exc) -> int | str:
    status = getattr(exc, "status_code", None)
    return status if isinstance(status, int) else "unknown"


def load_api_key(env_file) -> str:
    """The key from the git-ignored .env file, without printing or logging it."""
    from dotenv import dotenv_values

    value = dotenv_values(env_file).get(KEY_ENV)
    if not value or not value.strip():
        raise ValueError(f"{KEY_ENV} is not set in the environment file")
    return value.strip()
