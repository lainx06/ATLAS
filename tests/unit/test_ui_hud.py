"""The HUD components (docs/UI_DESIGN_HUD.md §4–§7): every bound value equals the run's own
files, absent fields read "not recorded", nothing is drawn for a run without an executed
candidate or with changed evidence, motion is switchable, and IDs are unique per instance.

The runs are the bundled recordings in demo/recorded (read only; tampering uses copies).
"""

import dataclasses
import html as html_lib
import json
import re
import shutil
import tomllib
from html.parser import HTMLParser
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import results as RS

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"
HAR_CLEAN = "t09/agent-har_clean-ac63eaecd7a8"
OUTCOME_CLASSES = ("hud-ret", "hud-code", "hud-c-", "hud-t-", "hud-outcome")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def assertion(path: Path, assertion_id: str) -> dict:
    return next(
        a for a in read(path)["assertions"] if a["assertion_id"] == assertion_id
    )


def load(
    label: str, run_dir: Path | None = None, **kw
) -> tuple[Path, dict, list, H.Hud]:
    d = run_dir or BUNDLE / label
    report = A.read_json(d / "agent_report.json")
    checks = R.verify(d, report)
    return d, report, checks, H.build(d, report, checks, label, **kw)


class Tags(HTMLParser):
    """Every start tag with its attributes, and the text."""

    def __init__(self, markup: str):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.text: list[str] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def all(self, tag: str, cls: str | None = None) -> list[dict]:
        return [
            a
            for t, a in self.tags
            if t == tag and (cls is None or cls in (a.get("class") or "").split())
        ]

    @property
    def joined(self) -> str:
        return "".join(self.text)


@pytest.fixture(scope="module")
def live6():
    return load(LIVE6)


# -- bound values ------------------------------------------------------------------------------
def test_leak_map_cells_equal_the_files(live6):
    d, _report, _checks, h = live6
    orig = assertion(d / "original/checks/split_integrity.json", H.LEAK_ASSERTION)
    cand = assertion(d / "candidates/c1/checks/split_integrity.json", H.LEAK_ASSERTION)
    groups = orig["observed"]["overlapping_groups"]
    folds = [s["fold"] for s in read(d / "original/splits.json")]
    assert folds == ["fold0", "fold1", "fold2", "fold3"]
    assert orig["status"] == "FAIL" and orig["observed"]["column"] == "subject_id"
    assert cand["status"] == "PASS" and cand["observed"]["overlapping_groups"] == {}
    expected_rows = []
    for listed in groups.values():
        expected_rows += [g for g in listed if g not in expected_rows]
    assert h.rows == expected_rows == [f"S0{i}" for i in range(1, 9)]

    for data, scope, source in (
        (h.leak_orig, "orig", groups),
        (h.leak_cand, "cand", cand["observed"]["overlapping_groups"]),
    ):
        tags = Tags(H.leak_map(data, h.rows, h.ids, scope, played=True))
        cells = tags.all("td")
        assert len(cells) == 8 * 4
        for g in h.rows:
            for f in folds:
                both = g in source.get(f, [])
                text = H.BOTH if both else H.NONE_SHARED
                cell = next(c for c in cells if c["title"] == f"{g}, {f}: {text}")
                assert cell["aria-label"] == cell["title"]
                assert ("hud-both" if both else "hud-none") in cell["class"]
        assert [th for th in tags.all("th") if th.get("scope") == "col"][1:] == [
            {"scope": "col", "title": f"{data.folds_source} · fold"} for _ in folds
        ]
        assert H.LEAK_Y_LABEL in tags.joined
        assert (
            data.source in tags.joined and "observed.overlapping_groups" in tags.joined
        )
    # 8 groups x 4 folds on both sides in the original; none in the candidate.
    assert (
        H.leak_map(h.leak_orig, h.rows, h.ids, "orig", played=True).count("hud-both")
        == 32
    )
    assert "hud-both" not in H.leak_map(h.leak_cand, h.rows, h.ids, "cand", played=True)


def test_fit_scope_flow_equals_the_files(live6):
    d, _report, _checks, h = live6
    orig = assertion(d / "original/checks/fit_provenance.json", H.FIT_ASSERTION)
    cand = assertion(d / "candidates/c1/checks/fit_provenance.json", H.FIT_ASSERTION)
    (origin,) = orig["observed"]["origins"]
    assert (origin["class"], origin["fit_scope"], origin["contributing_rows"]) == (
        "SelectKBest",
        "global",
        160,
    )
    assert len(origin["affected_folds"]) == 4
    html = H.fit_flow(h.flow_orig, h.ids, "orig", played=True)
    tags = Tags(html)
    texts = tags.joined
    for part in ("[160 rows] →", "SelectKBest", "(fit: global)"):
        assert part in texts
    for use in origin["affected_uses"]:
        fold, _, name = use.partition(":")
        assert fold in texts and name in texts
    lines = tags.all("path", "hud-fl")
    assert len(lines) == len(origin["affected_uses"]) == 8
    assert all("hud-fl-red" in p["class"] for p in lines)  # the assertion FAILs
    # The candidate's own file: PASS, no origins key at all. The PASS state is shown from the
    # recorded fields; "not recorded" is not printed for the origins it does not list.
    assert cand["status"] == "PASS" and "origins" not in cand["observed"]
    # Item 5 (story slice 1): every recorded fit event names its fold, so the candidate's
    # per-fold fits are drawn from those fields, one green lane per fold.
    events = [
        json.loads(line)
        for line in (d / "candidates/c1/provenance.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    fits = [(e["fold"], e["class"]) for e in events if e.get("type") == "fit"]
    cand_folds = [s["fold"] for s in read(d / "candidates/c1/splits.json")]
    assert len(fits) == 12 and {f for f, _ in fits} == set(cand_folds)
    lanes = {}
    for fold, cls in fits:
        lanes.setdefault(fold, []).append(cls)
    assert h.flow_cand.fold_fits == list(lanes.items())
    html = H.fit_flow(h.flow_cand, h.ids, "cand", played=True)
    tags = Tags(html)
    drawn = tags.all("path", "hud-fl")
    assert len(drawn) == len(fits) and all("hud-fl-green" in p["class"] for p in drawn)
    assert [(p["data-fold"], p["data-lane"]) for p in drawn] == [
        (f, str(list(lanes).index(f))) for f, _ in fits
    ]
    assert "hud-fl-red" not in html
    assert (
        "candidates/c1/provenance.jsonl · events type fit · fold, class" in tags.joined
    )
    # Without the fold fields (never derived from row sets) the PASS summary is shown.
    html = H.fit_flow(
        dataclasses.replace(h.flow_cand, fold_fits=None), h.ids, "cand", played=True
    )
    assert "<svg" not in html and "hud-fl-red" not in html
    tags = Tags(html)
    folds = len(read(d / "candidates/c1/splits.json"))
    violations = sum(len(v) for v in cand["observed"]["violations"].values())
    expected = (
        f"{violations} violations across {folds} folds · "
        f"{cand['observed']['judged_uses']} uses judged · "
        f"{len(cand['observed']['unknown_uses'])} unknown · no global fit origins listed"
    )
    assert expected == (
        "0 violations across 4 folds · 20 uses judged · 0 unknown · "
        "no global fit origins listed"
    )
    assert expected in tags.joined and H.NOT_RECORDED not in tags.joined
    for part in (
        "candidates/c1/checks/fit_provenance.json",
        H.FIT_ASSERTION,
        "observed.judged_uses",
        "observed.unknown_uses",
        "observed.violations",
        "candidates/c1/splits.json · fold",
    ):
        assert part in tags.joined, part


def test_fit_scope_without_origins_prints_not_recorded_only_where_a_value_is_expected():
    ids = H.Ids("0" * 8)

    def line(flow):
        return Tags(H.fit_flow(flow, ids, "orig", played=True)).joined

    # A FAIL with no origins field: the origins it needs are genuinely absent.
    fail = H.Flow("original", True, "FAIL", None, 3, 0, 1, folds=4, violation_entries=2)
    text = line(fail)
    assert "observed.origins: not recorded" in text
    assert "2 violations across 4 folds · 3 uses judged · 0 unknown" in text
    # A FAIL that lists an empty origins list: recorded as none.
    empty = H.Flow("original", True, "FAIL", [], 3, 0, 1, folds=4, violation_entries=2)
    assert "observed.origins: none listed" in line(empty)
    assert H.NOT_RECORDED not in line(empty)
    # A PASS with no origins field and every count recorded: no "not recorded" at all.
    ok = H.Flow("original", True, "PASS", None, 25, 0, 0, folds=5, violation_entries=0)
    assert H.NOT_RECORDED not in line(ok)
    assert (
        "0 violations across 5 folds · 25 uses judged · 0 unknown · no global fit "
        "origins listed"
    ) in line(ok)
    # A PASS whose splits.json is not verified: only the fold count is not recorded.
    no_folds = H.Flow("original", True, "PASS", None, 25, 0, 0, violation_entries=0)
    assert line(no_folds).count(H.NOT_RECORDED) == 1
    assert "0 violations (original/splits.json: not recorded)" in line(no_folds)


def test_har_clean_fit_scope_passes_from_its_recorded_fields():
    d, _report, _checks, h = load(HAR_CLEAN)
    fit = assertion(d / "original/checks/fit_provenance.json", H.FIT_ASSERTION)
    assert fit["status"] == "PASS" and "origins" not in fit["observed"]
    text = Tags(H.fit_flow(h.flow_orig, h.ids, "orig", played=True)).joined
    folds = len(read(d / "original/splits.json"))
    assert (
        f"0 violations across {folds} folds · {fit['observed']['judged_uses']} uses judged · "
        f"{len(fit['observed']['unknown_uses'])} unknown · no global fit origins listed"
    ) in text
    assert H.NOT_RECORDED not in text


def _lines(html: str) -> list[tuple[int, str, float, float]]:
    """(lane, use, start y, end y) of every flow line."""
    out = []
    for lane, use, d in re.findall(
        r'<path class="hud-fl[^"]*" pathLength="1" data-lane="(\d+)" data-use="([^"]+)" '
        r'd="([^"]+)"',
        html,
    ):
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
        out.append((int(lane), html_lib.unescape(use), nums[1], nums[-1]))
    return out


def test_several_origins_get_one_lane_each_bound_to_their_recorded_uses():
    d, _report, _checks, h = load(HAR_FLAWED)
    fit = assertion(d / "original/checks/fit_provenance.json", H.FIT_ASSERTION)
    origins = fit["observed"]["origins"]
    assert [o["class"] for o in origins] == ["StandardScaler", "SelectKBest"]
    html = H.fit_flow(h.flow_orig, h.ids, "orig", played=True)
    lines = _lines(html)
    # Every line is one recorded affected use of its own origin, and every use has its line.
    for k, o in enumerate(origins):
        drawn = sorted(use for lane, use, _, _ in lines if lane == k)
        assert drawn == sorted(o["affected_uses"]), o["class"]
    assert len(lines) == sum(len(o["affected_uses"]) for o in origins) == 10
    titles = re.findall(r"<title>([^<]+)</title></path>", html)
    assert len(titles) == 10 and all("→" in t for t in titles)
    # Lanes do not overlap: each lane's lines start and end inside its own vertical band.
    bands = {}
    for lane, _, y0, y1 in lines:
        lo, hi = bands.get(lane, (1e9, -1e9))
        bands[lane] = (min(lo, y0, y1), max(hi, y0, y1))
    assert bands[0][1] < bands[1][0], bands
    # The targets are listed once per origin (each lane lists its five uses).
    assert html.count('class="hud-ft">LogisticRegression.predict</text>') == 10


def test_reticles_equal_the_files_and_carry_the_caveat(live6):
    d, _report, _checks, h = live6
    orig = read(d / "original/outcome.json")
    cand = read(d / "candidates/c1/outcome.json")
    fails = sum(a["status"] == "FAIL" for a in orig["assertions"])
    assert (h.original.code, h.original.detail) == (
        orig["outcome"],
        f"{fails} of {len(orig['assertions'])} required checks FAIL",
    )
    assert h.original.detail == "4 of 9 required checks FAIL"
    assert h.candidate.code == cand["outcome"] == "NO_VIOLATION_FOUND"
    assert h.candidate.detail == "4 FAIL → PASS"
    execution = read(d / "candidates/c1/execution.json")
    assert (execution["runner"], execution["status"]) == (
        "docker_isolated",
        "completed",
    )
    assert h.candidate.execution == H.TYPED_APPROVAL
    hero = H.hero(h, played=True)
    tags = Tags(hero)
    reticles = tags.all("section", "hud-ret")
    assert len(reticles) == 2
    for code in (orig["outcome"], cand["outcome"]):
        assert code in tags.joined
        assert A.OUTCOME_LABELS[code] in tags.joined
    assert tags.joined.count(A.CAVEAT) == 2
    assert "original/outcome.json · outcome" in tags.joined
    assert "candidates/c1/outcome.json · outcome" in tags.joined
    assert "VALID" not in tags.joined.replace("INVALID", "").replace(
        "VIOLATION", ""
    ).replace("NO_VIOLATION", "")
    assert len(tags.all("span", "hud-br")) == 8  # brackets on the two reticles only


def test_ring_has_one_lit_segment_per_verified_item(live6):
    _d, _report, checks, h = live6
    assert len(checks) == 49 and R.intact(checks)
    tags = Tags(H.ring(checks, h.ids, played=True, phrase="p"))
    segs = tags.all("path", "hud-seg")
    assert len(segs) == 49 and all("hud-seg-ok" in s["class"] for s in segs)
    assert (
        "49/49" in tags.joined
        and "Integrity: 49 of 49 recorded items verified now (46 file hashes, 3 outcome comparisons)"
        in tags.joined
    )


def test_check_matrix_equals_the_outcomes(live6):
    d, report, _checks, h = live6
    orig = {
        a["assertion_id"]: a["status"]
        for a in read(d / "original/outcome.json")["assertions"]
    }
    cand = {
        a["assertion_id"]: a["status"]
        for a in read(d / "candidates/c1/outcome.json")["assertions"]
    }
    assert [(r.assertion_id, r.original, r.candidate) for r in h.matrix] == [
        (k, orig[k], cand[k]) for k in orig
    ]
    # The same as the report's status_by_assertion.
    sba = report["comparison"]["candidates"][0]["status_by_assertion"]
    assert [(s["assertion_id"], s["original"], s["candidate"]) for s in sba] == [
        (r.assertion_id, r.original, r.candidate) for r in h.matrix
    ]
    html = H.matrix_column(h.matrix, "cand", "candidates/c1/outcome.json", played=True)
    moves = re.findall(r'<span class="hud-move">([^<]+)</span>', html)
    assert moves == ["FAIL → PASS"] * 4


def test_track_and_gauge_equal_the_report(live6):
    _d, report, _checks, h = live6
    track = Tags(H.track(report, h.ids))
    stages = track.all("li", "hud-stage")
    assert len(stages) == len(report["states"]) == 16
    assert "BUDGET_EXHAUSTED" in track.joined
    for text in ("5 of 6", "5 of 12", "2 of 2"):
        assert text in track.joined
    gauge = Tags(H.gauge(report, h.ids))
    assert (
        "estimate, not billing" in gauge.joined.lower()
        or "Estimate, not billing" in (gauge.joined)
    )
    assert (
        f"{len(report['cost']['entries'])} of {report['spending']['max_attempts']}"
        in (gauge.joined)
    )
    assert (
        f"{report['cost']['estimated_total_usd']} of {report['spending']['estimate_cap_usd']}"
        in gauge.joined
    )
    har = A.read_json(BUNDLE / HAR_FLAWED / "agent_report.json")
    assert har["cost"]["reason"] in Tags(H.gauge(har, h.ids)).joined


# -- absent fields -----------------------------------------------------------------------------
def test_absent_fields_render_not_recorded():
    ids = H.Ids("0" * 8)
    absent = H.Leak("original", False, None, None, None, None)
    assert H.NOT_RECORDED in H.leak_map(absent, [], ids, "orig", played=True)
    no_groups = H.Leak("original", True, "FAIL", None, None, ["fold0"])
    assert "observed.overlapping_groups: not recorded" in H.leak_map(
        no_groups, [], ids, "orig", played=True
    )
    no_folds = H.Leak("original", True, "FAIL", None, {"fold0": ["S1"]}, None)
    html = H.leak_map(no_folds, ["S1"], ids, "orig", played=True)
    assert "original/splits.json: not recorded" in html
    assert "column not recorded" in html
    flow = H.Flow("original", True, "PASS", None, None, None, None)
    summary = Tags(H.fit_flow(flow, ids, "orig", played=True)).joined
    for field in (
        "observed.violations",
        "observed.judged_uses",
        "observed.unknown_uses",
    ):
        assert f"{field}: {H.NOT_RECORDED}" in summary, field
    assert H.NOT_RECORDED in H.fit_flow(
        H.Flow("original", False, None, None, None, None, None),
        ids,
        "orig",
        played=True,
    )
    origin = {"affected_uses": ["fold0:X.predict"], "affected_folds": ["fold0"]}
    svg = Tags(
        H.fit_flow(
            H.Flow("o", True, "FAIL", [origin], 1, 0, 1), ids, "orig", played=True
        )
    ).joined
    assert "[rows not recorded] →" in svg and "class not recorded" in svg
    assert "(fit: not recorded)" in svg
    o = H.Outcome("orig", "Before", None, "s", "d", "ds")
    assert "outcome: not recorded" in H.reticle(o, played=True)
    track = H.track({}, ids)
    assert "states: not recorded" in track and track.count(H.NOT_RECORDED) == 4
    gauge = H.gauge({"cost": {"applicable": True}, "spending": {}}, ids)
    assert "not recorded of not recorded" in gauge


# -- runs without an executed candidate, and changed evidence -----------------------------------
@pytest.mark.parametrize("label", [HAR_FLAWED, HAR_CLEAN])
def test_a_run_without_an_executed_candidate_has_no_after(label):
    d, _report, _checks, h = load(label)
    assert h.candidate is None and h.leak_cand is None and h.flow_cand is None
    hero, ev = H.hero(h, played=False), H.evidence(h, played=False)
    assert len(Tags(hero).all("section", "hud-ret")) == 1
    for absent in ("Verified revision", "hud-pane-cand", 'type="radio"', "→ PASS"):
        assert absent not in hero + ev
    orig = assertion(d / "original/checks/split_integrity.json", H.LEAK_ASSERTION)
    groups = orig["observed"]["overlapping_groups"]
    assert len(h.rows) == len({g for v in groups.values() for g in v})
    leak = H.leak_map(h.leak_orig, h.rows, h.ids, "orig", played=True)
    if label == HAR_FLAWED:
        assert len(h.rows) == 21 and leak.count('class="hud-both') == 21 * 5
        flow = H.fit_flow(h.flow_orig, h.ids, "orig", played=True)
        assert (
            "StandardScaler" in flow and "SelectKBest" in flow and "7352 rows" in flow
        )
    else:
        assert h.rows == [] and "No group is listed" in leak


def test_a_proposal_that_was_not_executed_gets_no_after(live6):
    d, report, checks, _h = live6
    # Without the candidate's verified files, nothing about it is shown.
    only_original = [c for c in checks if not c.item.startswith("candidates/")]
    h = H.build(d, report, only_original, LIVE6)
    assert h.candidate is None and "Verified revision" not in H.hero(h, played=True)
    # A report whose candidate was refused (not executed) has no after either.
    refused = json.loads(json.dumps(report))
    refused["comparison"]["candidates"][0]["run_dir"] = "c9"
    assert H.build(d, refused, checks, LIVE6).candidate is None


def test_changed_evidence_shows_no_outcome_and_no_diagram(tmp_path):
    copy = tmp_path / "live6"
    shutil.copytree(BUNDLE / LIVE6, copy)
    target = copy / "candidates/c1/outcome.json"
    data = bytearray(target.read_bytes())
    i = next(i for i, b in enumerate(data) if chr(b).isdigit())
    data[i] = ord(str((int(chr(data[i])) + 1) % 10))
    target.write_bytes(bytes(data))
    _d, _report, checks, h = load(LIVE6, copy)
    assert h is None and not R.intact(checks)
    ring = H.ring(checks, H.Ids(H.run_hash(LIVE6)), played=False, phrase="p")
    tags = Tags(ring)
    bad = [c for c in checks if not c.ok]
    assert len(tags.all("path", "hud-seg-bad")) == len(bad) == 1
    assert "EVIDENCE" in tags.joined and "CHANGED" in tags.joined
    assert "candidates/c1/outcome.json" in tags.joined
    for absent in ("VIOLATION_FOUND", "hud-ret", "hud-lm", "hud-flow", "hud-tile"):
        assert absent not in ring


# -- model-written frame, motion, toggle ----------------------------------------------------------
def test_the_model_written_frame_never_uses_outcome_styling(tmp_path):
    """The frame is native: badge, label, then the text as st.text (never HTML or Markdown).
    The outcome headline is a `## :<colour>[CODE]` heading; the frame has no heading, no
    outcome code and no HUD markup, and nothing in it animates."""
    script = tmp_path / "frame.py"
    script.write_text(
        "from atlas.ui import views as V\n"
        "V.model_text('<b>VIOLATION_FOUND</b> $x$', 'model-written text; not evidence', 'model-x')\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=30)
    at.run()
    assert not at.exception
    assert [m.value for m in at.markdown] == [H.MODEL_BADGE_MARKDOWN]
    assert H.MODEL_BADGE_MARKDOWN == ":orange-badge[MODEL-WRITTEN · UNTRUSTED]"
    assert [c.value for c in at.caption] == ["model-written text; not evidence"]
    assert [t.value for t in at.text] == [
        "<b>VIOLATION_FOUND</b> $x$"
    ]  # verbatim, inert
    for value in [m.value for m in at.markdown] + [c.value for c in at.caption]:
        assert not value.startswith("#") and "VIOLATION_FOUND" not in value
        for cls in OUTCOME_CLASSES + ("hud-anim", "hud-a-"):
            assert cls not in value


def test_played_renders_the_final_state_without_animation_classes(live6):
    _d, _report, checks, h = live6
    for played, expect in ((True, False), (False, True)):
        markup = (
            H.hero(h, played=played)
            + H.evidence(h, played=played)
            + H.ring(checks, h.ids, played=played, phrase="p")
        )
        assert ("hud-anim" in markup) is expect
        assert ("hud-a-" in markup) is expect
        assert ("animation-delay" in markup) is expect
    assert H.once_css(True) == "" and "hud-fade" in H.once_css(False)


def test_motion_respects_reduced_motion():
    css = H.CSS
    assert "@media (prefers-reduced-motion: reduce)" in css
    no_pref = css.index("@media (prefers-reduced-motion: no-preference)")
    assert css.index("@keyframes") > no_pref
    assert all(m.start() > no_pref for m in re.finditer(r"animation:hud-", css))
    assert "infinite" not in css  # nothing loops
    assert "prefers-reduced-motion: no-preference" in H.once_css(False)


def test_the_narrow_toggle_is_plain_html(live6):
    _d, _report, _checks, h = live6
    tags = Tags(H.evidence(h, played=True))
    radios = tags.all("input")
    assert [r["type"] for r in radios] == ["radio", "radio"]
    assert all("checked" not in r for r in radios)  # React would freeze a checked input
    assert {lab["for"] for lab in tags.all("label")} == {r["id"] for r in radios}


# -- text alternatives and IDs ----------------------------------------------------------------------
def test_every_diagram_has_a_text_alternative(live6):
    _d, _report, _checks, h = live6
    markup = H.hero(h, played=True) + H.evidence(h, played=True)
    tags = Tags(markup)
    ids = {a["id"] for _, a in tags.tags if "id" in a}
    for svg in tags.all("svg"):
        assert svg["role"] == "img"
        assert all(ref in ids for ref in svg["aria-labelledby"].split())
    assert len(tags.all("title")) >= 2 and len(tags.all("desc")) >= 2
    for region in [a for _, a in tags.tags if a.get("role") == "region"]:
        assert region["tabindex"] == "0" and region["aria-label"]
    for table in tags.all("table", "hud-lm"):
        assert table
    assert len(tags.all("caption")) == 2
    assert all(th.get("scope") in ("col", "row") for th in tags.all("th"))


def _blocks(h: H.Hud, report: dict) -> list[str]:
    return [
        H.hero(h, played=False),
        H.evidence(h, played=False),
        H.track(report, h.ids),
        H.gauge(report, h.ids),
    ]


def test_ids_are_unique_and_every_reference_resolves_in_its_instance(live6):
    _d, report, _checks, h = live6
    _, har_report, _, har = load(HAR_FLAWED)
    _, _, _, again = load(
        LIVE6, instance="x"
    )  # the same run rendered twice on one page
    blocks = _blocks(h, report) + _blocks(har, har_report) + _blocks(again, report)
    seen: list[str] = []
    refs = 0
    for block in blocks:
        tags = Tags(block)
        local = [a["id"] for _, a in tags.tags if "id" in a]
        seen += local
        for _, attrs in tags.tags:
            wanted = []
            for value in attrs.values():
                wanted += re.findall(r"url\(#([^)]+)\)", value or "")
            if (attrs.get("href") or "").startswith("#"):
                wanted.append(attrs["href"][1:])
            wanted += (attrs.get("aria-labelledby") or "").split()
            if attrs.get("for"):
                wanted.append(attrs["for"])
            for ref in wanted:
                refs += 1
                assert ref in local, ref
        for i in local:
            assert re.fullmatch(
                r"atlas-[a-z]+-[a-z]+-(orig|cand|run)-[0-9a-f]{8}-[a-z0-9]+", i
            ), i
    assert len(seen) == len(set(seen)), [i for i in set(seen) if seen.count(i) > 1]
    assert refs > 10
    assert f"atlas-flow-arrow-orig-{H.run_hash(LIVE6)}-h" in seen
    assert f"atlas-flow-arrow-orig-{H.run_hash(LIVE6)}-x" in seen


# -- escaping, tokens, contrast ------------------------------------------------------------------
def test_strings_from_files_cannot_leave_the_markup():
    hostile = "<img src=x onerror=1>\n\n[a](javascript:x) $x$ :red[y] `c` *b*"
    out = H.esc(hostile)
    for bad in ("<", ">", "\n", "](", "$", ":", "[", "`", "*"):
        assert bad not in out
    leak = H.Leak("original", True, "FAIL", hostile, {"fold0": [hostile]}, ["fold0"])
    html = H.leak_map(leak, [hostile], H.Ids("0" * 8), "orig", played=True)
    assert "<img" not in html and "\n" not in html
    assert Tags(html).joined.count(hostile) >= 1  # shown, unchanged, as text


def test_theme_matches_the_tokens_and_every_pair_meets_4_5():
    theme = tomllib.loads(
        (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
    )["theme"]
    assert theme["base"] == "dark"
    assert (theme["backgroundColor"], theme["secondaryBackgroundColor"]) == (
        H.BG,
        H.PANEL,
    )
    assert (theme["textColor"], theme["borderColor"], theme["primaryColor"]) == (
        H.TEXT,
        H.HAIRLINE,
        H.ACCENT,
    )
    for key, value in {
        "red": H.RED,
        "green": H.GREEN,
        "orange": H.AMBER,
        "violet": H.VIOLET,
        "gray": H.STONE,
    }.items():
        assert theme[f"{key}Color"] == theme[f"{key}TextColor"] == value
    for key, value in H.BADGE_BG.items():
        assert theme[f"{key}BackgroundColor"] == value
    fonts = {(f["family"], f["weight"], f.get("style")) for f in theme["fontFaces"]}
    assert ("IBM Plex Mono", 500, "normal") in fonts and len(fonts) == 9
    for face in theme["fontFaces"]:
        assert (ROOT / "static" / face["url"].removeprefix("app/static/")).is_file()
        assert not face["url"].startswith("http")
    assert (ROOT / "static/fonts/OFL.txt").is_file()
    for fg, bg, where in H.CONTRAST_PAIRS:
        assert H.contrast(fg, bg) >= 4.5, (fg, bg, where)


# -- the page: play once, no widget for the toggle, the render boundary ----------------------------
@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_HOSTED", "1")
    monkeypatch.setenv("ATLAS_HOSTED_RUNS_DIR", str(tmp_path / "hosted-runs"))
    for name in (
        "NEBIUS_API_KEY",
        "DATABASE_URL",
        "JUDGE_ACCESS_CODE",
        "HOSTED_LIVE_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)


def hud_markdown(at) -> str:
    return "\n".join(str(m.value) for m in at.markdown if 'class="hud' in str(m.value))


def test_the_hosted_recorded_page_plays_once_and_uses_no_widget_for_the_toggle(hosted):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception
    first = hud_markdown(at)
    assert "hud-anim" in first and "hud-ret" in first and 'type="radio"' in first
    assert [r.label for r in at.radio] == []  # the toggle is not a Streamlit widget
    assert at.session_state[RS.HUD_PLAYED] == {LIVE6}
    at.run()  # a rerun renders the final state
    second = hud_markdown(at)
    assert "hud-ret" in second and "hud-anim" not in second and "hud-a-" not in second


def test_a_render_failure_clears_the_hud_with_the_cards(hosted, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(H, "evidence", boom)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    assert [e.value for e in at.error] == [RS.RENDER_FAILED]
    assert "hud-ret" not in hud_markdown(at)
    assert "VIOLATION_FOUND" not in "\n".join(str(m.value) for m in at.markdown)
