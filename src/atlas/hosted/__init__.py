"""Hosted mode (T-12; SPEC §13 "Limited hosted"). Selected only by `ATLAS_HOSTED=1`.

In hosted mode the page shows recorded runs in the hash-verifying viewer and offers one live
model session per visitor session. The model inspects and proposes; every proposal passes
`validate_diff`, and nothing executes on the host ("not executed here"). The original's
findings come from a recorded, hash-verified trusted evaluation (`bundle.recorded_original`).
Every live request is reserved in the server-side budget store first (`budget_store`).

Without `ATLAS_HOSTED=1` nothing here is used: the local build is unchanged.
"""

import os

HOSTED_ENV = "ATLAS_HOSTED"


def enabled(env=None) -> bool:
    """True only when ATLAS_HOSTED is exactly "1"."""
    return (env if env is not None else os.environ).get(HOSTED_ENV) == "1"
