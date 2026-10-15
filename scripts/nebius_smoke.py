"""T-04 Nebius smoke: exactly one short chat completion, capped, with no retries, tools or loop.

Two tests, chosen with --test:
- text (default): connectivity; asks for a fixed reply.
- json: asks in the prompt for a fixed JSON object and validates the whole reply with a
  strict Pydantic schema. This is application-validated output, not provider-enforced
  structured output: no response_format is sent, because no NVIDIA model on Nebius lists
  json_mode or structured_outputs.

Dry run (default, free): reads .env without printing the key, re-reads model prices from
the authenticated GET /models, and prints the request and its maximum cost. Nothing is
generated and nothing is billed.

    uv run --locked python scripts/nebius_smoke.py

Paid run (one POST /chat/completions, after the same free price check):

    uv run --locked python scripts/nebius_smoke.py --execute [--test json]

Sanitized evidence goes to runs/nebius_smoke/ (git-ignored). The key is never printed or
saved. Any mismatch with the expected prices or limits aborts before the paid request.
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from openai import APIConnectionError, APIStatusError, OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
EVIDENCE_DIR = ROOT / "runs" / "nebius_smoke"

MODEL_ID = "nvidia/nemotron-3-super-120b-a12b"
# USD per token, as returned by the authenticated GET /models?verbose=true on 2026-10-14
# ($0.30 / $0.90 per 1M input / output tokens). Re-checked live before every run.
EXPECTED_PRICE_PROMPT = Decimal("0.0000003")
EXPECTED_PRICE_COMPLETION = Decimal("0.0000009")
EXPECTED_PRICE_REQUEST = Decimal(0)

# Documented by Nebius as "an upper bound for the number of tokens that can be generated
# for a completion, including visible output tokens and reasoning tokens."
MAX_COMPLETION_TOKENS = 1024
# The prompt is ~25 words; 512 is a deliberately loose ceiling covering chat-template overhead.
PROMPT_TOKEN_CEILING = 512
COST_LIMIT_USD = Decimal("0.01")
TIMEOUT_S = 60.0

PROMPTS = {
    "text": "This is a connectivity test. Reply with exactly the text: ATLAS smoke OK",
    "json": (
        "Reply with exactly this JSON object and nothing else. "
        "Do not use Markdown or code fences.\n"
        '{"project":"ATLAS","status":"ok"}'
    ),
}


class SmokeReply(BaseModel):
    """The whole reply must be this object. Nothing is extracted from prose or repaired."""

    model_config = ConfigDict(extra="forbid", strict=True)

    project: Literal["ATLAS"]
    status: Literal["ok"]


def validate_json_reply(content: str | None) -> dict:
    """Validate the entire content; only surrounding whitespace is removed."""
    if content is None:
        return {"passed": False, "errors": ["no message content"]}
    try:
        SmokeReply.model_validate_json(content.strip())
    except ValidationError as exc:
        errors = exc.errors(include_url=False, include_input=False)
        return {
            "passed": False,
            "errors": [f"{e['type']} at {e['loc']}: {e['msg']}" for e in errors],
        }
    return {"passed": True, "errors": []}


def load_env() -> tuple[str, str]:
    vals = dotenv_values(ENV_FILE)
    key = (vals.get("NEBIUS_API_KEY") or "").strip()
    base = (vals.get("NEBIUS_BASE_URL") or "").rstrip("/")
    if not key or key == "replace_with_local_secret":
        sys.exit("NEBIUS_API_KEY is not set in .env")
    if not base.startswith("https://"):
        sys.exit("NEBIUS_BASE_URL is missing or not https")
    return key, base


def max_cost(prices: dict) -> Decimal:
    return (
        PROMPT_TOKEN_CEILING * Decimal(prices["prompt"])
        + MAX_COMPLETION_TOKENS * Decimal(prices["completion"])
        + Decimal(prices["request"])
    )


def check_model(client: OpenAI) -> dict:
    """Free metadata call. Aborts unless the model, prices and context length are as expected."""
    page = client.models.list(extra_query={"verbose": "true"})
    models = {m.id: m.to_dict() for m in page}
    if MODEL_ID not in models:
        sys.exit(f"{MODEL_ID} is not in GET /models")
    model = models[MODEL_ID]
    prices = model["pricing"]
    expected = (
        EXPECTED_PRICE_PROMPT,
        EXPECTED_PRICE_COMPLETION,
        EXPECTED_PRICE_REQUEST,
    )
    live = (
        Decimal(prices["prompt"]),
        Decimal(prices["completion"]),
        Decimal(prices["request"]),
    )
    if live != expected:
        sys.exit(
            f"price changed: expected {expected}, live {live}; re-verify before running"
        )
    if PROMPT_TOKEN_CEILING + MAX_COMPLETION_TOKENS > model["context_length"]:
        sys.exit("token caps exceed the model context length")
    return model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--execute", action="store_true", help="send the one paid request"
    )
    parser.add_argument("--test", choices=sorted(PROMPTS), default="text")
    args = parser.parse_args()

    key, base = load_env()
    body = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": PROMPTS[args.test]}],
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "temperature": 0,
        "n": 1,
        "stream": False,
    }
    # max_retries=0: the SDK default (2) would retry 408/409/429/5xx and connection errors.
    with OpenAI(api_key=key, base_url=base, max_retries=0, timeout=TIMEOUT_S) as client:
        model = check_model(client)
        bound = max_cost(model["pricing"])
        print(f"model:        {MODEL_ID} (context {model['context_length']})")
        print(
            f"prices (USD/token): prompt {model['pricing']['prompt']}, "
            f"completion {model['pricing']['completion']}, request {model['pricing']['request']}"
        )
        print(
            f"caps:         prompt <= {PROMPT_TOKEN_CEILING} (ceiling), "
            f"max_completion_tokens = {MAX_COMPLETION_TOKENS} (incl. reasoning)"
        )
        print(f"max cost:     ${bound:.6f} (limit ${COST_LIMIT_USD})")
        print("request body:", json.dumps(body))
        if bound > COST_LIMIT_USD:
            sys.exit("maximum cost exceeds the limit; not sending")
        if not args.execute:
            print("dry run: no inference request sent")
            return 0

        started = datetime.now(UTC).isoformat()
        t0 = time.monotonic()
        data = error = None
        try:
            raw = client.chat.completions.with_raw_response.create(**body)
            status, headers, data = raw.status_code, raw.headers, raw.parse()
        except APIStatusError as exc:
            status, headers, error = exc.status_code, exc.response.headers, exc
        # Includes timeouts. The server may still have generated (and billed) tokens.
        except APIConnectionError as exc:
            status, headers, error = None, {}, exc
        elapsed = time.monotonic() - t0

    record = {
        "test": args.test,
        "started_utc": started,
        "elapsed_s": round(elapsed, 3),
        "http_status": status,
        "request_id": headers.get("x-request-id"),
        "request": body,
        "retries": 0,
        "max_cost_usd": str(bound),
    }
    if data is not None:
        usage = data.usage.to_dict() if data.usage else {}
        message = data.choices[0].message
        record.update(
            model=data.model,
            finish_reason=data.choices[0].finish_reason,
            content=message.content,
            reasoning_chars=len(message.to_dict().get("reasoning_content") or ""),
            usage=usage,
        )
        cost = (
            Decimal(usage.get("prompt_tokens", 0)) * EXPECTED_PRICE_PROMPT
            + Decimal(usage.get("completion_tokens", 0)) * EXPECTED_PRICE_COMPLETION
        )
        record["computed_cost_usd"] = str(cost)
        record["within_caps"] = (
            usage.get("completion_tokens", 0) <= MAX_COMPLETION_TOKENS
            and usage.get("prompt_tokens", 0) <= PROMPT_TOKEN_CEILING
        )
        if args.test == "json":
            record["output_enforcement"] = (
                "application-validated: prompt-requested JSON checked by a strict Pydantic "
                "schema; no response_format sent; not provider-enforced structured output"
            )
            record["validation"] = validate_json_reply(message.content)
    else:
        response = getattr(error, "response", None)
        record["error"] = type(error).__name__
        record["error_body"] = (
            response.text[:2000] if response is not None else str(error)
        )

    text = json.dumps(record, indent=2)
    if key in text:  # never persist the key, even if a server echoed it
        sys.exit("refusing to save evidence: response contains the API key")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / f"{args.test}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    print("evidence:", out.relative_to(ROOT))
    ok = data is not None and record["within_caps"]
    if args.test == "json":
        ok = ok and record["validation"]["passed"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
