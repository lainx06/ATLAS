"""Production Nebius Token Factory client (SPEC §11; T-06 slice 3). Offline-verified only.

This client has never sent a real request: it is tested with a mocked HTTP transport. A live
run (T-06 slice 4) needs separate, explicit authorization, reviewed ceilings, a justified
prompt-token bound and a model ID confirmed by the authenticated `GET /models`.

What it does with one request:

- **No hidden retries.** The SDK's retries are disabled (`max_retries=0`); the controller owns
  the single retry per transient call and the six-attempt limit.
- **Validated configuration.** Every value in `NebiusConfig` is required and checked before
  any SDK object exists, within an explicit supported range: integer token ceilings from 1
  and a template allowance from 0, both at most 10**100; a positive timeout of at most one
  day; finite non-negative `Decimal` prices of at most 10**100 USD per token with at most 30
  decimal places (`agent/money.py`). There are no built-in ceilings, timeouts or prices; the
  live values are a lead decision.
- **An input estimate, not a proven bound.** Before sending, `check_request` refuses a prompt
  whose *estimated* token count exceeds `max_input_tokens` (refused requests are never
  dispatched). The estimate is the UTF-8 byte length of the message text plus the configured
  `template_overhead_tokens` per message. It would be an upper bound only if no token covered
  less than one byte of text and the allowance covered the chat template; neither assumption
  has been verified for this model, so the estimate guarantees neither the prompt's token count
  nor the maximum charge. Justifying a bound is an open lead decision before any live run.
- **Validated reply metadata.** Reported usage is checked before anything else
  (`client.sanitize_usage`): a count is known only as a genuine non-negative integer. Invalid
  usage fails closed (`invalid_usage`), and only the validated counts and the invalid fields'
  names are kept, never a rejected value. Known usage above either ceiling is an error
  (`usage_over_ceiling`), charged at the known usage. The request ID and served model are kept
  only as short plain identifiers that do not contain the key, and the finish reason only from
  the known set.
- **Application-validated output.** The prompt asks for JSON; no `response_format`, tools or
  streaming are sent, and nothing on the provider side constrains the format. The controller
  validates the finish reason and the whole reply before any action.
- **No credential exposure.** The key is passed to the SDK only. Errors are classified by
  exception type and HTTP status only: provider and SDK messages (which can echo request text)
  are never used, and the SDK exception is not chained to the error raised here.
- **Cost figures for accounting.** `component_costs(usage)` prices each known count at the
  listed prices (None for an unknown count); `component_ceilings()` prices each ceiling. All of
  it is exact arithmetic in a private context (`agent/money.py`), independent of the caller's
  `decimal` settings, within the supported range checked by `NebiusConfig`. The ledger keeps
  an unknown component at its ceiling. Nothing here authorizes spending.
"""

import math
from dataclasses import dataclass
from decimal import Decimal

import httpx2
import openai

from atlas.agent import money
from atlas.agent.client import (
    MAX_TOKEN_COUNT,
    ModelError,
    ModelReply,
    ModelRequest,
    ModelTimeout,
    TransientModelError,
    safe_finish_reason,
    safe_identifier,
    sanitize_usage,
)

KEY_ENV = "NEBIUS_API_KEY"
MAX_TIMEOUT_S = 86_400  # the supported range for the per-request timeout (one day)


@dataclass(frozen=True)
class NebiusConfig:
    """Every field is required; the values for a live run are a lead decision (slice 4)."""

    base_url: str
    model_id: str
    max_input_tokens: int
    max_completion_tokens: int
    template_overhead_tokens: int  # per message, for the input estimate
    timeout_s: float
    price_input_per_token: Decimal
    price_output_per_token: Decimal
    # The provider's documented per-request limit on input plus output tokens (model metadata
    # from the authenticated `GET /models`); the basis of the provider-enforced worst case.
    context_length_tokens: int

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Raise TypeError or ValueError for an invalid field (its name only, never a value)."""
        if not isinstance(self.base_url, str) or not self.base_url.startswith(
            "https://"
        ):
            raise ValueError("base_url must be an https:// URL")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be a non-empty string")
        for name, minimum in (
            ("max_input_tokens", 1),
            ("max_completion_tokens", 1),
            ("template_overhead_tokens", 0),
            ("context_length_tokens", 2),
        ):
            value = getattr(self, name)
            if type(value) is not int:  # excludes bool and fractions
                raise TypeError(f"{name} must be an integer")
            if not minimum <= value <= MAX_TOKEN_COUNT:
                raise ValueError(f"{name} must be from {minimum} to 10**100")
        if (
            self.max_input_tokens + self.max_completion_tokens
            > self.context_length_tokens
        ):
            raise ValueError(
                "max_input_tokens plus max_completion_tokens must fit context_length_tokens"
            )
        timeout = self.timeout_s
        if type(timeout) not in (int, float):  # excludes bool
            raise TypeError("timeout_s must be a number of seconds")
        # Compared before any float conversion, so a huge integer cannot overflow here.
        if isinstance(timeout, float) and not math.isfinite(timeout):
            raise ValueError("timeout_s must be finite")
        if not 0 < timeout <= MAX_TIMEOUT_S:
            raise ValueError(f"timeout_s must be positive and at most {MAX_TIMEOUT_S}")
        for name in ("price_input_per_token", "price_output_per_token"):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be a Decimal")
            problem = money.price_problem(value)
            if problem is not None:
                raise ValueError(f"{name} {problem}")
        # The derived amounts must be exactly representable too (always true in this range;
        # checked so that no client exists if they were not).
        for tokens, price in (
            (self.max_input_tokens, self.price_input_per_token),
            (self.max_completion_tokens, self.price_output_per_token),
        ):
            money.cost(tokens, price)

    # -- cost figures (no client or key needed, so limits can be checked before either) ---------
    def component_ceilings(self) -> tuple[Decimal, Decimal]:
        return (
            money.cost(self.max_input_tokens, self.price_input_per_token),
            money.cost(self.max_completion_tokens, self.price_output_per_token),
        )

    def ceiling_cost(self) -> Decimal:
        return money.total(self.component_ceilings())

    def worst_case_request_cost(self) -> Decimal:
        """The most one request can cost if only the provider's documented limits hold (the
        input estimate failing entirely): input plus output within `context_length_tokens`,
        output within `max_completion_tokens`, at the listed prices. It relies on the provider
        enforcing both limits as documented, which ATLAS has not verified."""
        out = self.max_completion_tokens
        priced_output = money.total(
            (
                money.cost(
                    self.context_length_tokens - out, self.price_input_per_token
                ),
                money.cost(out, self.price_output_per_token),
            )
        )
        all_input = money.cost(self.context_length_tokens, self.price_input_per_token)
        return all_input if money.exceeds(all_input, priced_output) else priced_output


class NebiusClient:
    live = True

    def __init__(self, config: NebiusConfig, api_key: str, *, http_client=None):
        if not isinstance(config, NebiusConfig):
            raise TypeError("config must be a NebiusConfig")
        config.validate()  # again here: no SDK object is built from an invalid configuration
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

    def redact_secret(self, text: str, marker: str = "<redacted>") -> str:
        """`text` with this client's key replaced by `marker` (T-06 slice 4f), so the
        controller can scrub untrusted text without ever holding the key."""
        secret = self._sdk.api_key
        return text.replace(secret, marker) if secret else text

    # -- the input estimate and cost ----------------------------------------------------------
    def input_bound(self, request: ModelRequest) -> int:
        """The input estimate: assumption-dependent, not a proven bound (module docstring)."""
        total = 0
        for message in request.messages:
            content = message.get("content")
            text = content if isinstance(content, str) else ""
            total += len(text.encode("utf-8")) + self.config.template_overhead_tokens
        return total

    def user_message_budget(self, system_prompt: str) -> int:
        """The UTF-8 bytes left for the user message when the system prompt is the only other
        message: the input ceiling minus the system prompt's estimate and the user message's
        template allowance. A prompt within it passes `check_request` (same estimate)."""
        overhead = self.config.template_overhead_tokens
        fixed = len(system_prompt.encode("utf-8")) + overhead
        return max(0, self.config.max_input_tokens - fixed - overhead)

    def check_request(self, request: ModelRequest) -> None:
        if self.input_bound(request) > self.config.max_input_tokens:
            raise ModelError(
                "estimated prompt tokens exceed the input ceiling; not sent",
                code="input_over_ceiling",
                dispatched=False,
            )

    def component_ceilings(self) -> tuple[Decimal, Decimal]:
        return self.config.component_ceilings()

    def ceiling_cost(self) -> Decimal:
        return self.config.ceiling_cost()

    def worst_case_request_cost(self) -> Decimal:
        return self.config.worst_case_request_cost()

    def component_costs(self, usage) -> tuple[Decimal | None, Decimal | None]:
        """(input, output) cost of each validated known count; None for an unknown count."""
        counts, _ = sanitize_usage(usage)
        prompt, completion = counts["prompt_tokens"], counts["completion_tokens"]
        c = self.config
        return (
            None if prompt is None else money.cost(prompt, c.price_input_per_token),
            None
            if completion is None
            else money.cost(completion, c.price_output_per_token),
        )

    def usage_cost(self, usage) -> Decimal | None:
        """The cost of complete, valid usage; None if either count is unknown."""
        prompt, completion = self.component_costs(usage)
        if prompt is None or completion is None:
            return None
        return money.total((prompt, completion))

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
        except openai.OpenAIError:
            failure = ModelError("client error", code="client_error")
        if failure is not None:
            # Raised outside the except blocks: no chained SDK exception, request or headers.
            raise failure
        return self._reply(data, request_id)

    def _reply(self, data, request_id) -> ModelReply:
        # 1. Usage first: nothing below sees an unvalidated count.
        usage, invalid = sanitize_usage(getattr(data, "usage", None))
        if invalid:
            raise ModelError(
                "reported usage is invalid",
                code="invalid_usage",
                usage=usage,
                invalid_fields=invalid,
            )
        c = self.config
        prompt, completion = usage["prompt_tokens"], usage["completion_tokens"]
        if (prompt is not None and prompt > c.max_input_tokens) or (
            completion is not None and completion > c.max_completion_tokens
        ):
            raise ModelError(
                "reported usage exceeds a configured ceiling",
                code="usage_over_ceiling",
                usage=usage,
            )
        choices = getattr(data, "choices", None)
        if not isinstance(choices, list) or len(choices) != 1:
            raise ModelError(
                "unexpected number of choices", code="bad_response", usage=usage
            )
        choice = choices[0]
        content = getattr(getattr(choice, "message", None), "content", None)
        # 2. Provider-reported identifiers: kept only if plain and free of the key.
        secret = self._sdk.api_key
        withheld = []
        safe_request_id = safe_identifier(request_id, secret)
        if request_id is not None and safe_request_id is None:
            withheld.append("request_id")
        served = getattr(data, "model", None)
        safe_served = safe_identifier(served, secret)
        if served is not None and safe_served is None:
            withheld.append("served_model")
        return ModelReply(
            content=content if isinstance(content, str) else None,
            finish_reason=safe_finish_reason(getattr(choice, "finish_reason", None)),
            model_id=c.model_id,
            live=True,
            usage=usage,
            request_id=safe_request_id,
            served_model=safe_served,
            withheld=tuple(withheld),
            identifiers_checked=True,  # both were checked against the key above
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
