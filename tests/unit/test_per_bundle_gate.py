"""Release review 2, F2 (lead decision: per-bundle gating is the intended contract).

Each case card on the Overview is gated by its own bundle's verification at render time
(`story.card_codes`): with bundle A changed, card A shows no outcome code (only its
evidence-changed state) and A's story shows only the evidence-changed panel, while cards B and
C still show their outcomes, because their own bundles verify at render.
"""

import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import copy as C
from atlas.ui import story

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
OUTCOMES = {"VIOLATION_FOUND", "NO_VIOLATION_FOUND"}


def overview_app(bundle: str, selected: str) -> None:
    from pathlib import Path

    import streamlit as st

    from atlas.ui import story

    st.session_state[story.CASE] = selected
    story.overview(Path(bundle))


def _cards(at: AppTest) -> dict[str, str]:
    """Each case's card markup, found by its fixed description."""
    found = {}
    for case in C.CASES:
        found[case.key] = next(
            str(m.value)
            for m in at.markdown
            if "hud-case-codes" in str(m.value)
            and story.esc(case.description) in str(m.value)
        )
    return found


def _codes(card: str) -> set[str]:
    return {code for code in OUTCOMES if f">{code}<" in card.replace("&#95;", "_")}


@pytest.mark.parametrize("changed", [case.key for case in C.CASES])
@pytest.mark.parametrize("kind", ["one-byte", "forged"])
def test_each_card_is_gated_by_its_own_bundle(changed, kind, tmp_path):
    from test_report_race import tamper

    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    case = next(c for c in C.CASES if c.key == changed)
    tamper(bundle / case.run, kind)
    at = AppTest.from_function(
        overview_app, args=(str(bundle), changed), default_timeout=60
    ).run()
    assert not at.exception, at.exception
    cards = _cards(at)
    # Card A: its evidence-changed state only, no outcome code.
    assert C.CARD_CHANGED in cards[changed] and not _codes(cards[changed])
    # Cards B and C: their own bundles verify at render, so their outcomes show.
    for key, card in cards.items():
        if key != changed:
            assert _codes(card) and C.CARD_CHANGED not in card, key
    # A's story: only the evidence-changed panel (no verdict, no step, no report).
    page = "\n".join(
        str(x.value)
        for kind_ in ("markdown", "caption", "subheader", "text")
        for x in getattr(at, kind_)
        if "hud-case-codes" not in str(x.value)
    )
    assert C.EVIDENCE_CHANGED_CODE in page
    for token in (
        "hud-verdict",
        "hud-stepper",
        "hud-evidence",
        "recorded items verified",
    ):
        assert token not in page, token
    assert not at.get("download_button") and not at.toggle
