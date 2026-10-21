"""Record the pre-readability-pass baseline (`before.json`) for tests/unit/test_ui_readability.py.

Run once against the tree of commit b690af2 (the copy accuracy fix pass, before this pass),
with that tree's `src` first on the import path:

    git archive b690af2 | tar -x -C <tmp>
    PYTHONPATH=<tmp>/src uv run --locked python tests/fixtures/ui_readability/capture.py <tmp> <out>

It records, per bundled case, the plain view's five steps (each step expander's content) and
the Expert view of the Overview, the comparison page and How It Works & Limits.
"""

import json
import os
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "unit"))
from ui_capture import find, items

TREE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
APP = str(TREE / "app.py")
CASES = ("live6", "harflawed", "harclean")


def page(path: str | None, *, expert: bool, case: str | None = None) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["expert"] = expert
    if case is not None:
        at.session_state["story_case"] = case
    if path is not None:
        at.switch_page(path)
    at.run()
    assert not at.exception, at.exception
    return at


def main() -> None:
    os.environ.pop("ATLAS_HOSTED", None)
    from atlas.ui import story

    assert Path(story.__file__).resolve().is_relative_to(TREE), story.__file__
    out: dict = {"commit": "b690af2", "plain_steps": {}, "expert": {}}
    for case in CASES:
        at = page(None, expert=False, case=case)
        out["plain_steps"][case] = {
            str(n): items(find(at.main, f"step-{n}")) for n in range(1, 6)
        }
        out["expert"][f"overview_{case}"] = items(
            page(None, expert=True, case=case).main
        )
    out["expert"]["agent_vs_model"] = items(
        page("app_pages/agent_vs_model.py", expert=True).main
    )
    out["expert"]["how_it_works"] = items(
        page("app_pages/how_it_works.py", expert=True).main
    )
    OUT.write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


main()
