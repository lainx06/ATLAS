"""The evidence drill-down (UI design pass phase 2, part D).

Each FAIL, NOT_ASSESSED or ERROR tile of the check matrix opens an inspection frame
(details/summary in the same markup block: no Streamlit widget, no rerun) with that
assertion's recorded fields from its verified check file. Values equal the file; a list shows
its full count and "and <k> more"; IDs are unique per rendered instance.
"""

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from atlas.ui import artifacts as A
from atlas.ui import hud as H
from atlas.ui import recorded as R

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "demo" / "recorded"
LIVE6 = "live6/agent-s01_faulty-877f8245a8a2"
HAR_FLAWED = "t09/agent-har_flawed-1e2267f662c0"


def load(label: str, instance: str = "h") -> tuple[Path, H.Hud]:
    d = BUNDLE / label
    report = A.read_json(d / "agent_report.json")
    return d, H.build(d, report, R.verify(d, report), label, instance=instance)


def check_file(d: Path, base: str, aid: str) -> tuple[str, dict]:
    """The check file that records `aid` (what the drill-down must show)."""
    for p in sorted((d / base / "checks").glob("*.json")):
        for a in json.loads(p.read_text(encoding="utf-8"))["assertions"]:
            if a["assertion_id"] == aid:
                return p.relative_to(d).as_posix(), a
    raise AssertionError(aid)


class Frames(HTMLParser):
    """Each inspection frame's summary text, dt/dd pairs, limitation items and source."""

    def __init__(self, markup: str):
        super().__init__(convert_charrefs=True)
        self.frames: list[dict] = []
        self._stack: list[tuple[str, list[str]]] = []  # open elements and their text
        self._cur: dict | None = None
        self._dt: str | None = None
        self.ids: list[str] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        cls = (a.get("class") or "").split()
        if tag == "details" and "hud-insp" in cls:
            self._cur = {
                "summary": "",
                "pairs": [],
                "lims": [],
                "src": "",
                "labelled": "",
            }
            self.frames.append(self._cur)
        if self._cur is None:
            return
        if tag == "summary":
            self._cur["summary_id"] = a.get("id")
        if tag == "div" and "hud-insp-frame" in cls:
            self._cur["labelled"] = a.get("aria-labelledby")
        self._stack.append((tag if "hud-src" not in cls else "src", []))

    def handle_endtag(self, tag):
        if self._cur is None or not self._stack:
            return
        top, parts = self._stack.pop()
        text = "".join(parts)
        if top == "summary":
            self._cur["summary"] = text
        elif top == "dt":
            self._dt = text
        elif top == "dd":
            self._cur["pairs"].append((self._dt, text))
        elif top == "li":
            self._cur["lims"].append(text)
        elif top == "src":
            self._cur["src"] = text
        if tag == "details":
            self._cur = None

    def handle_data(self, data):
        for _, parts in self._stack:
            parts.append(data)


def frame_for(html: str, aid: str) -> dict:
    return next(f for f in Frames(html).frames if aid in f["summary"])


def expected_pairs(a: dict) -> list[tuple[str, str]]:
    def scalar(v):
        return v if isinstance(v, str) else json.dumps(v)

    pairs = [(k, scalar(a[k])) for k in ("status", "reason", "evidence_valid")]
    pairs += [(e["artifact"], e["sha256"]) for e in a["evidence"]]
    pairs += H.observed_rows(a["observed"])
    return pairs


def assert_frame_equals_file(d: Path, h: H.Hud, base: str, aid: str) -> dict:
    source, a = check_file(d, base, aid)
    side = "orig" if base == "original" else "cand"
    html = H.matrix_column(
        h.matrix,
        side,
        f"{base}/outcome.json",
        played=True,
        paired=h.candidate is not None,
        inspect=h.inspect_orig if side == "orig" else h.inspect_cand,
        ids=h.ids,
    )
    frame = frame_for(html, aid)
    assert frame["pairs"] == expected_pairs(a)
    assert frame["lims"] == a["limitations"]
    assert frame["src"] == f"{source} · assertions[assertion_id={aid}]"
    assert frame["labelled"] == frame["summary_id"]
    assert frame["summary"].startswith(a["status"])  # the tile itself: code, then ID
    return frame


def test_live6_drill_down_values_equal_the_check_files():
    d, h = load(LIVE6)
    group = assert_frame_equals_file(d, h, "original", "split.no_group_overlap")
    fit = assert_frame_equals_file(
        d, h, "original", "fit.state_dependencies_within_fold_train"
    )
    # Spot checks against the raw file values.
    _, a = check_file(d, "original", "split.no_group_overlap")
    fold0 = a["observed"]["overlapping_groups"]["fold0"]
    pairs = dict(group["pairs"])
    assert pairs["overlapping_groups.fold0"] == (
        f"{len(fold0)} items: " + "; ".join(fold0[:6]) + f" and {len(fold0) - 6} more"
    )
    assert pairs["splits.json"] == a["evidence"][0]["sha256"]  # full, never truncated
    assert len(pairs["splits.json"]) == 64
    _, f = check_file(d, "original", "fit.state_dependencies_within_fold_train")
    rows = dict(fit["pairs"])
    assert rows["judged_uses"] == str(f["observed"]["judged_uses"])
    assert rows["violating_folds"] == "4 items: fold0; fold1; fold2; fold3"
    assert rows["violations.fold0"].startswith(
        f"{len(f['observed']['violations']['fold0'])} items: {{class: StandardScaler"
    )


def test_har_flawed_drill_down_values_equal_the_check_file():
    d, h = load(HAR_FLAWED)
    statuses = {r.assertion_id: r.original for r in h.matrix}
    assert statuses["split.no_window_overlap"] == "NOT_ASSESSED"
    frame = assert_frame_equals_file(d, h, "original", "split.no_window_overlap")
    assert dict(frame["pairs"])["status"] == "NOT_ASSESSED"
    group = assert_frame_equals_file(d, h, "original", "split.no_group_overlap")
    _, a = check_file(d, "original", "split.no_group_overlap")
    fold0 = a["observed"]["overlapping_groups"]["fold0"]
    assert len(fold0) == 21
    assert dict(group["pairs"])["overlapping_groups.fold0"].startswith("21 items: ")
    assert dict(group["pairs"])["overlapping_groups.fold0"].endswith(" and 15 more")


def test_truncation_shows_the_true_count():
    assert H.list_text([]) == "0 items"
    assert H.list_text(["a"]) == "1 item: a"
    assert H.list_text(list("abcdef")) == "6 items: a; b; c; d; e; f"
    assert H.list_text(list("abcdefghij")) == "10 items: a; b; c; d; e; f and 4 more"
    nested = H.list_text([{"k": [1, 2, 3], "d": {"x": 1}, "s": "v"}])
    assert nested == "1 item: {k: [3 items], d: {1 keys}, s: v}"


def test_only_fail_not_assessed_and_error_tiles_open_a_frame():
    for label in (LIVE6, HAR_FLAWED):
        _, h = load(label)
        html = H.evidence(h, played=True)
        inspected = [r for r in h.matrix if r.original in H.INSPECTED] + [
            r for r in h.matrix if r.candidate in H.INSPECTED
        ]
        assert html.count('<details class="hud-insp">') == len(inspected)
        assert len(Frames(html).frames) == len(inspected)
    _, h = load(LIVE6)
    assert sorted(h.inspect_orig) == sorted(
        r.assertion_id for r in h.matrix if r.original == "FAIL"
    )
    assert h.inspect_cand == {}  # every candidate check PASSes


def test_the_drill_down_is_plain_markup_with_unique_ids():
    _, h = load(LIVE6)
    _, again = load(LIVE6, instance="x")
    _, har = load(HAR_FLAWED)
    ids: list[str] = []
    for hud in (h, again, har):
        parsed = Frames(H.evidence(hud, played=True))
        ids += parsed.ids
        for f in parsed.frames:
            assert f["summary_id"] and f["labelled"] == f["summary_id"]
    insp = [i for i in ids if i.startswith("atlas-insp-")]
    assert len(insp) == 4 + 4 + 5
    assert len(ids) == len(set(ids))
    for i in insp:
        assert re.fullmatch(
            r"atlas-insp-sum[a-z]+-(orig|cand)-[0-9a-f]{8}-[a-z0-9]+", i
        )
    html = H.evidence(h, played=True)
    for widget in ("<button", '<input type="checkbox"', "onclick", "<script"):
        assert widget not in html
    css = H.CSS
    assert ".hud summary.hud-tile-row:focus-visible{outline:2px solid #67E8F9" in css
    assert css.count(".hud-insp-frame{position:relative") == 1


def test_the_frame_escapes_what_it_reads():
    hostile = "<img src=x onerror=1>\n[a](javascript:x) $x$"
    item = H.Inspect(
        "a.b",
        "original/checks/x.json",
        {
            "status": "FAIL",
            "reason": hostile,
            "evidence_valid": True,
            "limitations": [hostile],
            "evidence": [{"artifact": hostile, "sha256": "0" * 64}],
            "observed": {"k": hostile, "l": [hostile]},
        },
    )
    body = H.record_body(item)
    assert "<img" not in body and "\n" not in body
    assert unescape(body).count(hostile) >= 3
