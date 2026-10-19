"""Server-side secrets for hosted mode (T-12 step 4).

Only these four are read, and only on the server: NEBIUS_API_KEY, DATABASE_URL,
JUDGE_ACCESS_CODE and HOSTED_LIVE_ENABLED. Each comes from `st.secrets` (Streamlit Community
Cloud's secret store) or, failing that, the process environment. Nothing here reads `.env`.
A value is returned to server code only; the page never renders, logs or reports one, and
the model key goes only to the production client.
"""

import os

NAMES = ("NEBIUS_API_KEY", "DATABASE_URL", "JUDGE_ACCESS_CODE", "HOSTED_LIVE_ENABLED")


def read(name: str) -> str | None:
    """A non-empty string secret, or None. Unknown names are refused."""
    if name not in NAMES:
        raise KeyError("not a hosted secret")
    value = None
    try:
        import streamlit as st

        value = st.secrets.get(name)
    except Exception:  # noqa: BLE001 - no secrets file, or no Streamlit: use the environment
        value = None
    if value is None:
        value = os.environ.get(name)
    return value if isinstance(value, str) and value else None
