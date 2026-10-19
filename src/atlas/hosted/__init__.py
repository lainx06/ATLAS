"""Hosted mode (T-12; SPEC §13 "Limited hosted"). Selected only by `ATLAS_HOSTED=1`.

In hosted mode the page shows recorded runs in the hash-verifying viewer and offers one live
model session per visitor session. The model inspects and proposes; every proposal passes
`validate_diff`, and nothing executes on the host ("not executed here"). The original's
findings come from a recorded, hash-verified trusted evaluation (`bundle.recorded_original`).
Every live request is reserved in the server-side budget store first (`budget_store`).

The hosted environment executes nothing, whichever way it is entered (T-12 fix pass 1): every
execution entry point calls `refuse_if_hosted` before any approval, file write, subprocess or
network access. They are `agent.controller.run_agent` (local, `hosted=False`),
`agent.controller.docker_original`, `agent.execute.execute_and_reevaluate`,
`runner.docker.run_candidate`, `runner.trusted.run_trusted_fixture`, `ui.worker.Registry.start`
and the `atlas.cli` audit and agent modes (exit 2). T-12 fix pass 2 adds every process start in
`runner.docker`: its two process helpers `_docker` and `_spawn`, and the maintenance entries
`build_image`, `probe` and `python -m atlas.runner.docker` (exit 2).

Without `ATLAS_HOSTED=1` nothing here is used: the local build is unchanged.
"""

import os

HOSTED_ENV = "ATLAS_HOSTED"


class HostedExecutionRefused(RuntimeError):
    """An execution entry point was reached with ATLAS_HOSTED=1; nothing was run."""


def enabled(env=None) -> bool:
    """True only when ATLAS_HOSTED is exactly "1"."""
    return (env if env is not None else os.environ).get(HOSTED_ENV) == "1"


def refuse_if_hosted(what: str, env=None) -> None:
    """Raise HostedExecutionRefused when hosted mode is on. The message names `what` and fixed
    text only, never an environment value."""
    if enabled(env):
        raise HostedExecutionRefused(
            f"{what} refused: the hosted environment executes nothing; nothing was run"
        )
