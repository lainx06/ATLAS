"""One integrity count everywhere (UI HUD fix pass 1).

The ring (title, centre and caption), the briefing and the evidence panel take their numbers
from the same verification result through `atlas.ui.hud.integrity_count`, in one unit
("recorded items") with a computed breakdown (file hashes, outcome comparisons). For live run 6,
both HAR bundles and a tampered copy, every count the page displays equals the counts of the
`verify` result, and the breakdown sums to the total.
"""

import re
import shutil
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as R

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"

PHRASE = re.compile(
    r"(\d+) of (\d+) recorded items (verified now|differ) "
    r"\((\d+) file hashes?, (\d+) outcome comparisons?\)"
)
CENTRE = re.compile(r">(\d+)/(\d+)</text>")
OLD_WORDING = re.compile(r"\d+ recorded hashes|\d+ of \d+ differ|All \d+ recorded")


def test_the_count_object():
    checks = [
        R.Check("a.json", "x", "x", "matches"),
        R.Check("b.json", "x", "y", "changed"),
        R.Check("agent_report.json:scientific_outcomes.original", "V", "V", "matches"),
    ]
    c = H.integrity_count(checks)
    assert (c.hashes, c.comparisons, c.differ, c.total) == (2, 1, 1, 3)
    assert (
        c.differing
        == "1 of 3 recorded items differ (2 file hashes, 1 outcome comparison)"
    )
    assert c.verified == (
        "2 of 3 recorded items verified now (2 file hashes, 1 outcome comparison)"
    )
    assert H.integrity_count([checks[0]]).verified == (
        "1 of 1 recorded items verified now (1 file hash, 0 outcome comparisons)"
    )


def tamper(copy: Path) -> None:
    target = copy / "candidates/c1/outcome.json"
    target.write_bytes(target.read_bytes().replace(b"PASS", b"PAS5", 1))


def page_texts(at: AppTest) -> list[str]:
    """Every string the page displays through markdown, captions and status elements."""
    out = [str(m.value) for m in at.markdown]
    for kind in (at.caption, at.error, at.warning, at.info, at.success):
        out += [str(e.value) for e in kind]
    return out


@pytest.mark.parametrize("label", [LIVE6, HAR_FLAWED, HAR_CLEAN, "tampered"])
def test_every_displayed_integrity_count_is_the_verification_results(
    label, monkeypatch, tmp_path
):
    source = LIVE6 if label == "tampered" else label
    shown_label = "ui/" + Path(source).name  # where the recorded-run list looks
    copy = tmp_path / shown_label
    shutil.copytree(BUNDLE / source, copy)
    if label == "tampered":
        tamper(copy)
    report = A.read_json(copy / "agent_report.json")
    checks = R.verify(copy, report)
    total = len(checks)
    differ = sum(1 for c in checks if not c.ok)
    # Classified without the helper's rule: report-key checks name a report file and a key.
    comparisons = sum(1 for c in checks if re.match(r"(agent_)?report\.json:", c.item))
    hashes = total - comparisons
    assert hashes + comparisons == total and (differ == 0) == (label != "tampered")

    monkeypatch.delenv("ATLAS_HOSTED", raising=False)
    monkeypatch.setenv(R.RECORDED_ENV, str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.switch_page("app_pages/try_it_live.py")  # the Try It Live page (navigation)
    at.session_state["view"] = "recorded"
    at.session_state["recorded_run"] = shown_label
    at.run()
    assert not at.exception
    texts = page_texts(at)
    joined = "\n".join(texts)

    matches = PHRASE.findall(joined)
    word = "verified now" if differ == 0 else "differ"
    # ring title and the briefing (intact), or ring title and the evidence-changed panel
    # (changed): the same phrase each time. The ring's caption carries no breakdown (story
    # slice 1: the breakdown is in the evidence panel only).
    assert len(matches) >= 2, joined
    for n_a, n_b, kind, h, c in matches:
        assert kind == word
        assert (int(n_b), int(h), int(c)) == (total, hashes, comparisons)
        assert int(h) + int(c) == int(n_b)  # the breakdown sums to the total
        if kind == "differ":
            assert int(n_a) == differ
        else:
            assert int(n_a) == total
    ring = [t for t in texts if 'class="hud hud-ring' in t]
    assert ring and all(OLD_WORDING.search(t) is None for t in texts)
    if differ == 0:
        assert CENTRE.findall(ring[0]) == [(str(total), str(total))]
        brief = next(t for t in texts if "hud-brief" in t)
        assert H.esc(f"Evidence intact: {H.integrity_count(checks).verified}.") in brief
        assert f":green-badge[intact] {H.integrity_count(checks).verified}:" in joined
        # One phrase in the ring's title, the briefing and the evidence panel.
        assert len(matches) == 3
    else:
        assert "hud-brief" not in joined and "Evidence intact" not in joined
        assert ":red-badge[EVIDENCE CHANGED]" in joined
        assert CENTRE.findall(ring[0]) == []  # no n/n centre on changed evidence
        assert f"{differ} of {total} recorded items differ</span>" in ring[0]  # caption
        assert len(matches) == 2
