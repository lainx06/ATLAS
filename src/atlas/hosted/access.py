"""Judge access (T-12): the typed access code selects the judge pool.

The typed code is compared with the JUDGE_ACCESS_CODE secret in constant time. A match selects
the judge route; anything else (a wrong code, or no configured code) falls back to the public
route, never to an error that spends. A failed attempt is recorded as an event with its time
only: the typed text is never logged, stored or shown, and neither is the configured code.

A configured code shorter than `MIN_CODE_LENGTH` (32) characters disables the judge route: it
is treated as not configured, so every visitor uses the public route, and an attempt records
the fixed event `judge_code_too_short` (no code text, no length). Generate the code with
`uv run --locked python -c "import secrets; print(secrets.token_urlsafe(32))"`.
"""

import hmac
from collections.abc import Callable

from atlas.hosted.budget_store import JUDGE, PUBLIC

REJECTED = "judge_code_rejected"
ACCEPTED = "judge_code_accepted"
UNCONFIGURED = "judge_code_unconfigured"
TOO_SHORT = "judge_code_too_short"
MIN_CODE_LENGTH = 32


def usable_code(expected: str | None) -> bool:
    """A configured code counts only if it is a string of at least MIN_CODE_LENGTH characters."""
    return isinstance(expected, str) and len(expected) >= MIN_CODE_LENGTH


def code_matches(typed: str | None, expected: str | None) -> bool:
    """Constant-time comparison; an empty entry, an unset code or a configured code shorter
    than MIN_CODE_LENGTH never matches."""
    if not isinstance(typed, str) or not usable_code(expected):
        return False
    if not typed:
        return False
    return hmac.compare_digest(typed.encode("utf-8"), expected.encode("utf-8"))


def select_route(
    typed: str | None, expected: str | None, log: Callable[[str, str], None]
) -> str:
    """JUDGE for the correct code, else PUBLIC. `log(route, event)` records only the route
    and a fixed event code (its failure never changes the route). A configured code that is
    too short disables the judge route (`TOO_SHORT`)."""
    if not typed:
        return PUBLIC
    if not expected:
        _quietly(log, JUDGE, UNCONFIGURED)
        return PUBLIC
    if not usable_code(expected):
        _quietly(log, JUDGE, TOO_SHORT)
        return PUBLIC
    if code_matches(typed, expected):
        _quietly(log, JUDGE, ACCEPTED)
        return JUDGE
    _quietly(log, JUDGE, REJECTED)
    return PUBLIC


def _quietly(log, route: str, event: str) -> None:
    try:
        log(route, event)
    except Exception:  # noqa: BLE001, S110 - diagnostics never decide the route
        pass
