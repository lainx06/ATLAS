"""Test-only server: the app in hosted mode with a mocked Token Factory (T-12 tests).

    python tests/hosted/hosted_server.py PORT

Before Streamlit starts, the pre-run check and the production client are routed to the mock
provider of `hosted_helpers` (no real provider is ever reachable), and Python networking in
this process is limited to loopback for its whole life (the browser connection and the local
test database). Each completion request is counted in `$ATLAS_TEST_PROVIDER_LOG`. This file
lives under tests/ and is never part of the hosted app.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hosted_helpers as H


class _Patch:
    def setattr(self, target, name, value):
        setattr(target, name, value)


def main() -> int:
    port = sys.argv[1]
    log = Path(os.environ["ATLAS_TEST_PROVIDER_LOG"])

    def count(request):
        with open(log, "a", encoding="utf-8") as f:
            f.write("post\n")

    replies = [H.completion(c) for c in [*H.LIVE6_REPLIES, H.FINISH]] * 10
    H.wire(_Patch(), H.Provider(replies, on_post=count))
    guard = H.loopback_only()
    attempts = guard.__enter__()  # held for the life of the process
    guard_log = Path(os.environ["ATLAS_TEST_GUARD_LOG"])

    def report_attempts():
        import time

        while True:  # the test reads this file; the process is killed at the end
            guard_log.write_text(",".join(attempts), encoding="utf-8")
            time.sleep(0.2)

    import threading

    threading.Thread(target=report_attempts, daemon=True).start()
    from streamlit.web import cli

    sys.argv = [
        "streamlit", "run", str(H.ROOT / "app.py"), "--server.port", port,
        "--server.headless", "true", "--server.address", "localhost",
        "--browser.gatherUsageStats", "false",
    ]  # fmt: skip
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())
