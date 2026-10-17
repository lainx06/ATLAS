"""T-06 slice 4 pre-run model check, as a standalone script (DECISIONS.md 2026-10-16, decision 4).

Dry run (default): prints the one planned request and the expected values from the decided
configuration (`budget.DECIDED_SLICE4`). It reads no key and sends nothing.

    uv run --locked python scripts/live_preflight.py

Execute (needs the lead's Gate 3 go-ahead): reads the key from the git-ignored `.env` (never
printed), sends the one free `GET /models?verbose=true` and no completion, and writes sanitized
evidence to `runs/preflight-<UTC time>.json`. Exits 0 on pass, 6 on abort.

    uv run --locked python scripts/live_preflight.py --execute
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from atlas.agent import money
from atlas.agent.budget import DECIDED_SLICE4
from atlas.agent.nebius import NebiusConfig, load_api_key
from atlas.agent.preflight import (
    PASS,
    PREFLIGHT_ABORT_EXIT,
    run_preflight,
    summary_lines,
)
from atlas.cli import CONFIG_KEYS

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
EVIDENCE_DIR = ROOT / "runs"


def decided_config() -> NebiusConfig:
    return NebiusConfig(**{k: DECIDED_SLICE4[k] for k in CONFIG_KEYS})


def plan(config: NebiusConfig) -> list[str]:
    return [
        "DRY RUN: nothing is sent and no key is read.",
        f"planned request: GET {config.base_url.rstrip('/')}/models?verbose=true",
        "  header: Authorization: Bearer <key from .env, never printed>",
        f"  timeout {config.timeout_s} s (proposed), no retries, no redirects, no completion",
        f"expected model: {config.model_id}",
        f"  listed input price per token:  {money.text(config.price_input_per_token)}",
        f"  listed output price per token: {money.text(config.price_output_per_token)}",
        f"  listed context length:         {config.context_length_tokens}",
        "Abort if the model is absent, any value differs, or the call fails in any way.",
    ]


def main(
    argv=None, *, env_file=ENV_FILE, evidence_dir=EVIDENCE_DIR, http_client=None
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--execute", action="store_true", help="send the one GET")
    args = parser.parse_args(argv)
    config = decided_config()
    if not args.execute:
        for line in plan(config):
            print(line)
        return 0
    key = load_api_key(env_file)
    evidence = run_preflight(config, key, http_client=http_client)
    del key
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = Path(evidence_dir) / f"preflight-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    for line in summary_lines(evidence):
        print(line)
    print(f"evidence: {path}")
    return 0 if evidence["result"] == PASS else PREFLIGHT_ABORT_EXIT


if __name__ == "__main__":
    sys.exit(main())
