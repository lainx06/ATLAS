"""T-03 hosting probe stub. Runs no ATLAS code.

Three separate checks, each reported on its own:
  1. build/import: the page renders, so the host built the environment and started Streamlit.
  2. secret store: a harmless canary secret is present (never the value of any real key).
  3. optional Nebius connectivity: `GET /models` only (no inference, no cost), shown only after an
     explicit button press and only if a NEBIUS_API_KEY secret was added by the owner.

The page never prints a secret's value. For the canary it shows only presence and a hash prefix.
"""

import hashlib
import json
import platform
import sys
import time
import urllib.error
import urllib.request

import streamlit as st

STARTED = time.time()
MODELS_URL = "https://api.tokenfactory.nebius.com/v1/models"


def secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):  # no secrets file: nothing configured
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


def nebius_models_check(key: str) -> dict:
    """One authenticated GET /models. Returns status and model count only; never the key."""
    request = urllib.request.Request(
        MODELS_URL, headers={"Authorization": f"Bearer {key}"}
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read())
            return {
                "http_status": response.status,
                "models": len(body.get("data", [])),
                "elapsed_s": round(time.time() - started, 2),
            }
    except urllib.error.HTTPError as exc:
        return {"http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"error": type(exc).__name__}


st.title("ATLAS hosting probe")
st.caption("Stub only. No ATLAS code, data or real keys.")

st.subheader("1. Build and import")
st.write(
    {
        "python": sys.version.split()[0],
        "streamlit": st.__version__,
        "platform": platform.platform(),
        "process_uptime_s": round(time.time() - STARTED, 1),
    }
)

st.subheader("2. Secret store (canary)")
st.write(canary_report())

st.subheader("3. Optional Nebius connectivity (GET /models only)")
if secret("NEBIUS_API_KEY") is None:
    st.write("No NEBIUS_API_KEY secret configured: skipped.")
elif st.button("Run GET /models"):
    st.write(nebius_models_check(secret("NEBIUS_API_KEY")))
