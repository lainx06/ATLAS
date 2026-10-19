"""Judge access (T-12): the typed access code selects the judge pool.

The typed code is compared with the JUDGE_ACCESS_CODE secret in constant time. A match selects
the judge route; anything else (a wrong code, or no configured code) falls back to the public
route, never to an error that spends. A failed attempt is recorded as an event with its time
only: the typed text is never logged, stored or shown, and neither is the configured code.
"""

import hmac
from collections.abc import Callable

from atlas.hosted.budget_store import JUDGE, PUBLIC

REJECTED = "judge_code_rejected"
ACCEPTED = "judge_code_accepted"
UNCONFIGURED = "judge_code_unconfigured"


def code_matches(typed: str | None, expected: str | None) -> bool:
    """Constant-time comparison; an empty entry or an unset code never matches."""
    if not isinstance(typed, str) or not isinstance(expected, str):
        return False
    if not typed or not expected:
        return False
    return hmac.compare_digest(typed.encode("utf-8"), expected.encode("utf-8"))


def select_route(
    typed: str | None, expected: str | None, log: Callable[[str, str], None]
) -> str:
    """JUDGE for the correct code, else PUBLIC. `log(route, event)` records only the route
    and a fixed event code (its failure never changes the route)."""
    if not typed:
        return PUBLIC
    if code_matches(typed, expected):
        _quietly(log, JUDGE, ACCEPTED)
        return JUDGE
    _quietly(log, JUDGE, REJECTED if expected else UNCONFIGURED)
    return PUBLIC


def _quietly(log, route: str, event: str) -> None:
    try:
        log(route, event)
    except Exception:  # noqa: BLE001, S110 - diagnostics never decide the route
        pass
