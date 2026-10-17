"""The worker process for one UI run: `python -m atlas.ui.runproc ...`.

Runs `atlas.audit.audit` or `run_agent` with a FixtureClient and the BrowserApprover, then
writes `result.json` (the run directory, or the exception type if the engine call raised) to
the channel directory. It is a separate process so that the engine's process-wide fixture
network guard never touches the Streamlit server.
"""

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="atlas.ui.runproc")
    p.add_argument("--channel", type=Path, required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--mode", choices=["audit", "agent"], required=True)
    p.add_argument("--script")
    p.add_argument("--runs-root", type=Path, required=True)
    args = p.parse_args(argv)

    from atlas.ui.catalogue import BY_NAME

    result = {"run_dir": None, "crash": None, "crash_detail": None}
    try:
        project = BY_NAME[args.project].path
        if args.mode == "audit":
            from atlas.audit import audit

            result["run_dir"] = str(audit(project, args.runs_root).run_dir)
        else:
            from atlas.agent.client import FixtureClient
            from atlas.agent.controller import run_agent
            from atlas.ui.approver import BrowserApprover
            from atlas.ui.scripts import BY_KEY

            script = BY_KEY[args.script]
            client = FixtureClient(f"ui-{script.key}", script.replies())
            run = run_agent(
                project, args.runs_root, client, BrowserApprover(args.channel)
            )
            result["run_dir"] = str(run.run_dir)
    except Exception as exc:  # noqa: BLE001 - shown on the page, never as a result
        result["crash"] = type(exc).__name__
        result["crash_detail"] = "".join(
            traceback.format_exception_only(type(exc), exc)
        ).strip()[:500]
    tmp = args.channel / "result.json.tmp"
    tmp.write_text(json.dumps(result), encoding="utf-8")
    os.replace(tmp, args.channel / "result.json")  # atomic: the page never reads half
    return 0


if __name__ == "__main__":
    sys.exit(main())
