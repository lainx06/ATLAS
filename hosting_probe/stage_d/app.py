"""ATLAS hosting probe, stage D: canary plus budget-store feasibility (synthetic units only).

Checks, reported separately. No provider key, no model request, no ATLAS code.
  1. Build/import and 2. secret canary, as in stage A.
  3. Optional budget-store probe: runs only after a button press and only if a DATABASE_URL secret
     exists. It uses scratch tables and synthetic integer units. It never prints the URL.
"""

import hashlib
import platform
import sys
import time

import budget_probe
import streamlit as st

STARTED = time.time()


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):  # no secrets configured
        return None
    return value if isinstance(value, str) and value else None


def canary_report() -> dict:
    value = secret("CANARY")
    if value is None:
        return {"present": False}
    return {
        "present": True,
        "sha256_prefix": hashlib.sha256(value.encode()).hexdigest()[:8],
    }


def run_budget_probe(url: str) -> list[dict]:
    import psycopg  # imported here so the page renders without a database driver

    def connect():
        return psycopg.connect(url, autocommit=True, connect_timeout=15)

    try:
        return budget_probe.run_all(connect)
    except Exception as exc:  # noqa: BLE001 - the type only: messages may contain the host name
        return [
            {
                "name": "budget probe",
                "ok": False,
                "detail": f"stopped: {type(exc).__name__}",
            }
        ]


st.title("ATLAS hosting probe: stage D")
st.caption(
    "Canary and budget-store probe. Synthetic units only. No provider key or request."
)

st.subheader("1. Build and import")
st.write(
    {
        "python": sys.version.split()[0],
        "streamlit": st.__version__,
        "platform": platform.platform(),
        "process_uptime_s": round(time.time() - STARTED, 1),
        "page_rendered_at_unix": int(time.time()),
    }
)

st.subheader("2. Secret store (canary)")
st.write(canary_report())

st.subheader("3. Budget-store probe (scratch tables, synthetic units)")
database_url = secret("DATABASE_URL")
if database_url is None:
    st.write("No DATABASE_URL secret configured: skipped.")
elif st.button("Run budget probe"):
    st.write(run_budget_probe(database_url))
