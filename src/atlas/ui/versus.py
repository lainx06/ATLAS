"""The ATLAS Checks vs. Model Alone page (UI restructure slice 2, part B): the T-11 live comparison.

Data comes only from the tracked result files in `evaluation/results/t11-live-20261019/`
(`results.md`, `scores.json`, `suite.json`) and `evaluation/expected.json`. Before anything is
shown, `verify` recomputes the three result files' SHA-256 and compares them with the values
recorded in that folder's README.md, and expected.json's with the hash `suite.json` recorded
for it. On any difference the page draws only the evidence-changed panel (no number), like
the run gate (`atlas.ui.results.gate`). This detects changes since recording; it does not
authenticate files whose recorded hashes were rewritten too.

Every number is computed from the verified files (`figures`); every sentence is fixed copy
(`atlas.ui.copy`), and the reviewed findings are copied exactly from docs/EVALUATION.md.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from atlas.ui import artifacts as A
from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import recorded as R
from atlas.ui import story
from atlas.ui import views as V
from atlas.ui.catalogue import ROOT

RESULTS_DIR = ROOT / "evaluation" / "results" / "t11-live-20261019"
EXPECTED = ROOT / "evaluation" / "expected.json"
RESULT_FILES = ("results.md", "scores.json", "suite.json")
_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|\s*$")
ACCENT, NEUTRAL = "#67E8F9", "#94A3B8"  # ATLAS (the one accent) and the model alone
INK, MUTED, GRID = "#E2E8F0", "#94A3B8", "#1E2A36"

CSS = """
<style>
.st-key-vs-head { gap: 8px 16px; align-items: flex-start; flex-wrap: wrap; }
.st-key-vs-head h1 { padding: 0 0 0.5rem; }
.st-key-vs-question p { font-size: 18px; line-height: 1.45; font-weight: 500; color: #E2E8F0; }
.st-key-vs-caveats, .st-key-vs-means { background: #0F1720; border: 1px solid #1E2A36;
  border-radius: 4px; padding: 10px 14px; }
.st-key-vs-caveats { border-left: 2px solid #FBBF24; }
.st-key-vs-means { border-left: 2px solid #67E8F9; }
.hud-vs ul { margin: 4px 0 0; padding-left: 18px; }
.hud-vs li { margin: 0 0 6px; font-size: 16px; line-height: 1.5; color: #E2E8F0; }
.hud-vs code { font-size: 12px; }
.hud-vs-chart svg { display: block; width: 100%; height: auto; }
.hud-vs-chart .vs-narrow { display: none; }
@media (max-width: 640px) {
  .hud-vs-chart .vs-wide { display: none; }
  .hud-vs-chart .vs-narrow { display: block; }
}
.hud-vs-chart { max-width: 860px; }
/* Readability pass: the answer, the caveat line and the stat tiles (plain view). */
.st-key-vs-answer p { font-size: 20px; line-height: 1.45; font-weight: 500; color: #E2E8F0; }
.st-key-vs-caveat-line { background: #0F1720; border: 1px solid #1E2A36;
  border-left: 2px solid #FBBF24; border-radius: 4px; padding: 8px 14px; }
.st-key-vs-caveat-line p { font-size: 16px; line-height: 1.5; margin: 0; }
.st-key-vs-caveat-line [data-testid="stMarkdownContainer"] { margin-bottom: 0; }
[class*="st-key-vs-tile-"] { gap: 4px; padding-bottom: 14px; }
[class*="st-key-vs-tile-"] [data-testid="stMetricValue"] > div { font-size: 30px; }
[class*="st-key-vs-tile-"] [data-testid="stCaptionContainer"] p { margin: 0; }
/* Final fix pass (F6): each caption directly under its own metric; labels wrap instead of
   being cut; the first tile's two labels share a two-line slot, bottom-aligned, so both values
   sit on one line. */
[class*="st-key-vs-side-"] { gap: 2px; }
[class*="st-key-vs-tile-"] [data-testid="stMetricLabel"],
[class*="st-key-vs-tile-"] [data-testid="stMetricLabel"] * { white-space: normal;
  overflow: visible; text-overflow: clip; }
.st-key-vs-tile-0 [data-testid="stMetricLabel"] { min-height: 2.8em; display: flex;
  align-items: flex-end; }
.st-key-vs-tile-0 [data-testid="stMetricLabel"] p { line-height: 1.4; }
</style>
"""


# -- the gate ------------------------------------------------------------------------------------
def recorded_hashes(readme: str) -> dict[str, str]:
    """The `| `file` | `sha256` |` rows of the results folder's README."""
    out = {}
    for line in readme.splitlines():
        m = _ROW.match(line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _file(path: Path, item: str, recorded: str | None) -> R.Check:
    if not path.is_file():
        return R.Check(item, recorded, None, "missing")
    digest = A.sha256_file(path)
    return R.Check(
        item, recorded, digest, "matches" if digest == recorded else "changed"
    )


def verify(
    results_dir: Path | None = None, expected: Path | None = None
) -> list[R.Check]:
    """The three result files against the README's recorded hashes, then expected.json
    against the hash recorded in (the verified) suite.json."""
    results_dir = Path(results_dir or RESULTS_DIR)
    expected = Path(expected or EXPECTED)
    try:
        readme = (results_dir / "README.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        readme = ""
    recorded = recorded_hashes(readme)
    checks = [
        _file(results_dir / name, name, recorded.get(name)) for name in RESULT_FILES
    ]
    suite = A.read_json(results_dir / "suite.json") if checks[2].ok else None
    want = ((suite or {}).get("inputs") or {}).get("expected.json")
    checks.append(
        _file(Path(expected), "expected.json", want if isinstance(want, str) else None)
    )
    return checks


# -- the figures (from the verified files only) ----------------------------------------------------
@dataclass(frozen=True)
class Figures:
    cases: int  # cases in the comparison
    repetitions: int
    atlas_found: int  # predeclared violations ATLAS found
    atlas_assessable: int  # predeclared violations ATLAS could assess
    expected_total: int  # all predeclared violations (summed over the flawed cases)
    not_assessed: int  # predeclared violations in ATLAS's coverage gaps
    same_found: int  # the model alone, on the ATLAS-assessable violations
    same_total: int
    same_ids: int  # the ATLAS-assessable violations, counted once per case
    all_found: int  # the model alone, on every predeclared violation (valid trials)
    all_total: int
    atlas_false: int
    model_false: int
    atlas_invalid: int  # ATLAS cases unavailable or with errors on expected IDs
    model_invalid: int
    trials: int
    flawed_valid: int  # the model's valid trials on cases with predeclared violations
    clean_valid: int  # the model's valid trials on cases with none
    recorded_runs: int
    reruns: int
    cost_usd: str


def _ids(case: dict) -> set[str]:
    return {
        e["assertion_id"]
        for e in case.get("expected_violated") or []
        if isinstance(e, dict) and isinstance(e.get("assertion_id"), str)
    }


def figures(scores: dict, suite: dict, expected: dict) -> Figures:
    atlas, base = scores["atlas"], scores["baseline"]
    want = {cid: _ids(c) for cid, c in expected["cases"].items()}
    gaps = {c["case_id"]: set(c.get("coverage_gaps") or []) for c in atlas["cases"]}
    same_found = same_total = flawed_valid = clean_valid = 0
    for case in base["cases"]:
        cid = case["case_id"]
        assessable = want[cid] - gaps.get(cid, set())
        for trial in case["trials"]:
            if trial.get("status") != "VALID":
                continue
            same_total += len(assessable)
            same_found += len(set(trial.get("tp") or []) & assessable)
            if want[cid]:
                flawed_valid += 1
            else:
                clean_valid += 1
    sources = suite.get("atlas_sources") or {}
    t = atlas["totals"]
    return Figures(
        cases=len(expected["cases"]),
        repetitions=int(suite["repetitions"]),
        atlas_found=t["tp"],
        atlas_assessable=t["tp"] + t["fn"],
        expected_total=sum(len(v) for v in want.values()),
        not_assessed=sum(len(want[c] & gaps.get(c, set())) for c in want),
        same_found=same_found,
        same_total=same_total,
        same_ids=sum(len(want[c] - gaps.get(c, set())) for c in want),
        all_found=base["totals"]["tp"],
        all_total=base["totals"]["tp"] + base["totals"]["fn"],
        atlas_false=t["fp"],
        model_false=base["totals"]["fp"],
        atlas_invalid=sum(
            1 for c in atlas["cases"] if not c.get("available") or c.get("errors")
        ),
        model_invalid=base["totals"]["invalid_reply"],
        trials=base["totals"]["trials_scheduled"],
        flawed_valid=flawed_valid,
        clean_valid=clean_valid,
        recorded_runs=sum(
            1 for v in sources.values() if str(v).startswith("recorded:")
        ),
        reruns=sum(1 for v in sources.values() if str(v).startswith("re-run:")),
        cost_usd=str((suite.get("spend") or {})["estimated_total_usd"]),
    )


def values(f: Figures) -> dict[str, str]:
    """The printed value of each bar (and of the data table)."""
    return {
        "fa": (C.VS_FOUND_ATLAS_GAP if f.not_assessed else C.VS_FOUND_ATLAS).format(
            k=f.atlas_found,
            n=f.atlas_assessable,
            x=f.not_assessed,
            t=f.expected_total,
        ),
        "fs": C.VS_FOUND_SAME.format(k=f.same_found, n=f.same_total),
        "fo": C.VS_FOUND_ALL.format(k=f.all_found, n=f.all_total),
        "fm": C.VS_FOUND_MODEL.format(
            ks=f.same_found,
            ns=f.same_total,
            m=f.same_ids,
            ka=f.all_found,
            na=f.all_total,
            t=f.expected_total,
        ),
        "xa": str(f.atlas_false),
        "xm": str(f.model_false),
        "ia": C.VS_NONE
        if f.atlas_invalid == 0
        else C.VS_OF.format(k=f.atlas_invalid, n=f.cases),
        "im": C.VS_OF.format(k=f.model_invalid, n=f.trials),
    }


def alt_text(f: Figures) -> str:
    return C.VS_ALT.format(**values(f))


def table(f: Figures) -> pd.DataFrame:
    v = values(f)
    return pd.DataFrame(
        [
            {
                C.VS_TABLE_MEASURE: C.VS_PANELS["found"],
                C.VS_SERIES_ATLAS: v["fa"],
                C.VS_SERIES_MODEL: v["fm"],
            },
            {
                C.VS_TABLE_MEASURE: C.VS_PANELS["false"],
                C.VS_SERIES_ATLAS: v["xa"],
                C.VS_SERIES_MODEL: v["xm"],
            },
            {
                C.VS_TABLE_MEASURE: C.VS_PANELS["invalid"],
                C.VS_SERIES_ATLAS: v["ia"],
                C.VS_SERIES_MODEL: v["im"],
            },
        ]
    )


# -- the chart (SVG, data-bound; three small panels, each with its own axis from zero) -------------
@dataclass(frozen=True)
class Bar:
    series: str  # "atlas" or "model"
    label: str  # the row label
    value: float  # the bar length, in the panel's unit
    text: str  # the printed value


def panels(f: Figures) -> list[tuple[str, float, list[float], list[Bar]]]:
    """(panel key, axis maximum, ticks, bars). Found: shares of each denominator (0 to 1);
    false alarms: counts; invalid answers: counts out of the scheduled replies."""
    v = values(f)
    top = max(2, f.model_false, f.atlas_false)
    return [
        (
            "found",
            1.0,
            [0.0, 0.5, 1.0],
            [
                Bar(
                    "atlas",
                    C.VS_SERIES_ATLAS,
                    f.atlas_found / f.atlas_assessable,
                    v["fa"],
                ),
                Bar(
                    "model",
                    C.VS_ROW_SAME.format(m=f.same_ids),
                    f.same_found / f.same_total,
                    v["fs"],
                ),
                Bar(
                    "model",
                    C.VS_ROW_ALL.format(n=f.expected_total),
                    f.all_found / f.all_total,
                    v["fo"],
                ),
            ],
        ),
        (
            "false",
            float(top),
            [float(x) for x in range(top + 1)],
            [
                Bar("atlas", C.VS_SERIES_ATLAS, f.atlas_false, v["xa"]),
                Bar("model", C.VS_SERIES_MODEL, f.model_false, v["xm"]),
            ],
        ),
        (
            "invalid",
            float(f.trials),
            [0.0, f.trials / 2, float(f.trials)],
            [
                Bar("atlas", C.VS_SERIES_ATLAS, f.atlas_invalid, v["ia"]),
                Bar("model", C.VS_SERIES_MODEL, f.model_invalid, v["im"]),
            ],
        ),
    ]


def _tick(key: str, x: float) -> str:
    return f"{round(x * 100)}%" if key == "found" else f"{x:g}"


def _bar_path(x0: float, y: float, w: float, h: float, r: float = 4.0) -> str:
    """A bar square at the baseline with a 4 px rounded data end."""
    r = min(r, w / 2, h / 2)
    x1 = x0 + w
    return (
        f"M{x0:.1f} {y:.1f}H{x1 - r:.1f}Q{x1:.1f} {y:.1f} {x1:.1f} {y + r:.1f}"
        f"V{y + h - r:.1f}Q{x1:.1f} {y + h:.1f} {x1 - r:.1f} {y + h:.1f}H{x0:.1f}Z"
    )


def chart_svg(f: Figures, *, narrow: bool, prefix: str = "atlas-vs") -> str:
    """The chart. Wide: row labels left of the bars. Narrow (phones): labels above the bars.
    Values are printed at each bar's end in text colours; series colour only on the marks."""
    W = 360 if narrow else 820
    left = 12 if narrow else 190
    right = 12 if narrow else 300  # room for "8 of 8 assessable (1 of 9 not assessed)"
    plot = W - left - right
    bar_h, gap = 18, (30 if narrow else 10)
    fill = {"atlas": ACCENT, "model": NEUTRAL}
    sid = f"{prefix}-{'n' if narrow else 'w'}"
    out, y = [], 16
    # Legend (two series: always present).
    lx = 12
    for series, name in (("atlas", C.VS_SERIES_ATLAS), ("model", C.VS_SERIES_MODEL)):
        out.append(
            f'<rect x="{lx}" y="{y - 10}" width="12" height="12" rx="2" '
            f'fill="{fill[series]}"/>'
            f'<text x="{lx + 18}" y="{y}" fill="{INK}" font-size="13">{H.esc(name)}</text>'
        )
        lx += 30 + 8 * len(name)
    y += 22
    for key, top, ticks, bars in panels(f):
        out.append(
            f'<text x="12" y="{y + 14}" fill="{INK}" font-size="14" font-weight="600">'
            f"{H.esc(C.VS_PANELS[key])}</text>"
            f'<text x="12" y="{y + 32}" fill="{MUTED}" font-size="12">'
            f"{H.esc(C.VS_PANEL_NOTES[key])}</text>"
        )
        y += 44
        rows_h = len(bars) * (bar_h + gap + (16 if narrow else 0))
        # Gridlines and ticks (hairline, solid, recessive).
        for t in ticks:
            x = left + plot * (t / top if top else 0)
            out.append(
                f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y + rows_h}" '
                f'stroke="{GRID}" stroke-width="1"/>'
                f'<text x="{x:.1f}" y="{y + rows_h + 14}" fill="{MUTED}" font-size="11" '
                f'text-anchor="middle">{H.esc(_tick(key, t))}</text>'
            )
        for bar in bars:
            if narrow:
                out.append(
                    f'<text x="{left}" y="{y + 12}" fill="{INK}" font-size="13">'
                    f"{H.esc(bar.label)}</text>"
                )
                y += 16
            else:
                out.append(
                    f'<text x="{left - 10}" y="{y + 13}" fill="{INK}" font-size="13" '
                    f'text-anchor="end">{H.esc(bar.label)}</text>'
                )
            w = plot * (bar.value / top) if top else 0
            title = f"{bar.label}: {bar.text}"
            out.append(f"<g><title>{H.esc(title)}</title>")
            if w > 0:
                out.append(
                    f'<path d="{_bar_path(left, y, w, bar_h)}" fill="{fill[bar.series]}"/>'
                )
            out.append(
                f'<rect x="{left}" y="{y}" width="{max(w, 24):.1f}" height="{bar_h}" '
                'fill="transparent"/>'
            )
            tx = left + w + 8
            anchor = "start"
            if narrow and tx > W - 110:
                tx, anchor = left + w - 8, "end"
                ink = "#0A0F14"
            else:
                ink = INK
            out.append(
                f'<text x="{tx:.1f}" y="{y + 13}" fill="{ink}" font-size="13" '
                f'font-weight="600" text-anchor="{anchor}">{H.esc(bar.text)}</text></g>'
            )
            y += bar_h + gap
        # The baseline (zero).
        out.append(
            f'<line x1="{left}" y1="{y - rows_h}" x2="{left}" y2="{y}" stroke="{MUTED}" '
            'stroke-width="1"/>'
        )
        y += 30
    title = C.VS_CHART_TITLE.format(c=f.cases)
    return (
        f'<svg class="vs-{"narrow" if narrow else "wide"}" viewBox="0 0 {W} {y}" '
        f'role="img" aria-labelledby="{sid}-title {sid}-desc" '
        f"font-family=\"'IBM Plex Sans', sans-serif\">"
        f'<title id="{sid}-title">{H.esc(title)}</title>'
        f'<desc id="{sid}-desc">{H.esc(alt_text(f))}</desc>' + "".join(out) + "</svg>"
    )


def chart(f: Figures) -> str:
    return (
        '<div class="hud hud-vs-chart">'
        + chart_svg(f, narrow=False)
        + chart_svg(f, narrow=True)
        + "</div>"
    )


# -- the page ----------------------------------------------------------------------------------------
def _list(key: str, head: str, items: list[str]) -> None:
    with st.container(key=key):
        st.markdown(
            f'<div class="hud hud-vs"><span class="hud-lbl">{H.esc(head)}</span><ul>'
            + "".join(f"<li>{story.code_html(x)}</li>" for x in items)
            + "</ul></div>",
            unsafe_allow_html=True,
        )


def caveats(f: Figures) -> list[str]:
    fields = {
        "rec": f.recorded_runs,
        "rerun": f.reruns,
        "k": f.model_invalid,
        "n": f.trials,
        "c": f.cases,
        "r": f.repetitions,
    }
    return [c.format(**fields) for c in C.VS_CAVEATS]


def changed_panel(checks: list[R.Check]) -> None:
    bad = [c for c in checks if not c.ok]
    with st.container(key="vs-changed", border=True):
        V.state_panel(
            "vs-integrity",
            "red",
            C.EVIDENCE_CHANGED_CODE,
            C.VS_CHANGED.format(d=len(bad), t=len(checks)),
            C.VS_CHANGED_ACTION,
        )
        st.table(
            pd.DataFrame(
                [
                    {
                        "result": c.status,
                        "file": c.item,
                        "recorded": c.recorded or "",
                        "recomputed now": c.recomputed or "",
                    }
                    for c in bad
                ]
            ),
            hide_index=True,
        )
        st.caption(C.VS_GATE_NOTE)


def page(results_dir: Path | None = None, expected: Path | None = None) -> None:
    """The page (the bundled result files unless others are given). Nothing is shown before
    `verify` finds every file intact."""
    results_dir = Path(results_dir or RESULTS_DIR)
    expected = Path(expected or EXPECTED)
    st.html(CSS)
    with st.container(key="vs-page"):
        with st.container(key="vs-head", horizontal=True):
            st.title(C.PAGE_AGENT)
            story.expert_toggle()
        if (
            story.expert()
        ):  # plain view: the question moves under "About this comparison"
            with st.container(key="vs-question"):
                st.markdown(story.md(C.VS_QUESTION))
        checks = verify(results_dir, expected)
        if not R.intact(checks):
            changed_panel(checks)
            return
        try:
            scores = json.loads((Path(results_dir) / "scores.json").read_text("utf-8"))
            suite = json.loads((Path(results_dir) / "suite.json").read_text("utf-8"))
            exp = json.loads(Path(expected).read_text("utf-8"))
            f = figures(scores, suite, exp)
        except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
            changed_panel([R.Check("scores.json", None, None, "changed")])
            return
        body(f, checks, scores, suite, exp)


def answer(f: Figures) -> str:
    """C1: the one answer sentence (every number from the verified files)."""
    return C.VS_ANSWER.format(
        c=f.cases,
        r=f.repetitions,
        k=f.atlas_found,
        ks=f.same_found,
        ns=f.same_total,
        m=f.same_ids,
        ka=f.all_found,
        na=f.all_total,
        xm=f.model_false,
        im=f.model_invalid,
        t=f.trials,
    )


def caveat_line(f: Figures) -> str:
    """C2: the one visible caveat line (the number of projects from the verified files)."""
    return C.VS_CAVEAT_LINE.format(c=f.cases)


def tiles(
    f: Figures,
) -> list[tuple[str, tuple[str, str, str | None], tuple[str, str, str | None]]]:
    """C3: (title, (label, value, caption) for ATLAS, the same for the model alone)."""
    v = values(f)
    return [
        (
            C.VS_TILE_FOUND,
            (
                C.VS_TILE_FOUND_ATLAS,
                C.VS_OF.format(k=f.atlas_found, n=f.atlas_assessable),
                C.VS_TILE_ATLAS_FOUND_NOTE.format(x=f.not_assessed, t=f.expected_total)
                if f.not_assessed
                else None,
            ),
            (
                C.VS_TILE_FOUND_MODEL,
                C.VS_OF.format(k=f.same_found, n=f.same_total),
                C.VS_TILE_MODEL_FOUND_NOTE.format(
                    m=f.same_ids, ka=f.all_found, na=f.all_total
                ),
            ),
        ),
        (
            C.VS_TILE_FALSE,
            (C.VS_SERIES_ATLAS, v["xa"], None),
            (C.VS_SERIES_MODEL, v["xm"], None),
        ),
        (
            C.VS_TILE_INVALID,
            (C.VS_SERIES_ATLAS, v["ia"], None),
            (C.VS_SERIES_MODEL, v["im"], None),
        ),
    ]


def stat_tiles(f: Figures) -> None:
    with st.container(key="vs-tiles"):
        for col, (i, (title, *sides)) in zip(
            st.columns(3), enumerate(tiles(f)), strict=True
        ):
            # height="stretch": the three tiles share one height (F6).
            with (
                col,
                st.container(key=f"vs-tile-{i}", border=True, height="stretch"),
            ):
                st.markdown(f"**{story.md(title)}**")
                for j, (side_col, (label, value, note)) in enumerate(
                    zip(st.columns(2), sides, strict=True)
                ):
                    with side_col, st.container(key=f"vs-side-{i}-{j}"):
                        st.metric(label, value)
                        if note:
                            st.caption(story.md(note))


def plain_body(f: Figures, checks: list) -> None:
    """Plain view (readability pass): the answer, the caveat line (all six behind a click),
    three stat tiles, the chart, then the details behind clicks and one footnote line."""
    with st.container(key="vs-answer"):
        st.markdown(story.md(answer(f)))
    with st.container(key="vs-caveat-line"):
        st.markdown(story.md(caveat_line(f)))
    items = caveats(f)
    with st.expander(C.VS_ALL_CAVEATS.format(n=len(items)), key="vs-all-caveats"):
        _list("vs-caveats", C.VS_CAVEATS_HEAD, items)
    stat_tiles(f)
    with st.container(key="vs-chart"):
        st.markdown(chart(f), unsafe_allow_html=True)
    with st.container(key="vs-chart-note"):
        st.caption(story.md(C.VS_CHART_NOTE.format(v=f.flawed_valid)))
    with (
        st.expander(C.VS_DATA_TABLE, key="vs-data-table"),
        st.container(key="vs-table"),
    ):
        st.table(table(f), hide_index=True)
    with st.expander(C.VS_MEANS_DETAIL, key="vs-means-detail"):
        _list("vs-means", C.VS_MEANS_HEAD, list(C.VS_MEANS_PLAIN))
        with st.container(key="vs-means-source"):
            st.caption(story.md(C.VS_MEANS_PLAIN_SOURCE))
    with st.expander(C.VS_ABOUT, key="vs-about"):
        with st.container(key="vs-question"):
            st.markdown(story.md(C.VS_QUESTION))
        st.markdown(story.md(C.VS_SETUP.format(r=f.repetitions, c=f.cases)))
    with st.container(key="vs-footnote"):
        st.caption(
            story.md(
                C.VS_FOOT_SEP.join(
                    (
                        C.VS_COST.format(usd=f.cost_usd),
                        C.VS_REVIEW,
                        C.VS_INTACT.format(v=len(checks), t=len(checks)),
                    )
                )
            )
        )


def body(f: Figures, checks: list, scores: dict, suite: dict, exp: dict) -> None:
    plain = not story.expert()
    if plain:
        plain_body(f, checks)
        return
    st.markdown(story.md(C.VS_SETUP.format(r=f.repetitions, c=f.cases)))
    _list("vs-caveats", C.VS_CAVEATS_HEAD, caveats(f))
    with st.container(key="vs-chart"):
        st.markdown(chart(f), unsafe_allow_html=True)
    with st.container(key="vs-chart-note"):
        st.caption(story.md(C.VS_CHART_NOTE.format(v=f.flawed_valid)))
    with st.container(key="vs-table"):
        st.table(table(f), hide_index=True)
    # Plain view: the four plain-words items; Expert view: the reviewed findings, exactly.
    shown = list(C.VS_MEANS_PLAIN if plain else C.T11_FINDINGS)
    _list("vs-means", C.VS_MEANS_HEAD, shown)
    with st.container(key="vs-means-source"):
        st.caption(story.md(C.VS_MEANS_PLAIN_SOURCE if plain else C.VS_FINDINGS_SOURCE))
    with st.container(key="vs-cost"):
        st.caption(story.md(C.VS_COST.format(usd=f.cost_usd)))
    with st.container(key="vs-review"):
        st.caption(story.md(C.VS_REVIEW if plain else C.VS_REVIEW_FULL))
    with st.container(key="vs-intact"):
        st.caption(story.md(C.VS_INTACT.format(v=len(checks), t=len(checks))))
    if plain:
        return
    expert(f, checks, scores, suite, exp)


def expert(f: Figures, checks: list, scores: dict, suite: dict, exp: dict) -> None:
    st.markdown(
        C.VS_EXPERT_RUN.format(
            run_dir=str(suite.get("run_dir") or H.NOT_RECORDED).replace("\\", "/"),
            model=suite.get("model_id"),
            seed=suite.get("seed"),
            policy=suite.get("policy_version"),
            r=f.repetitions,
            q=suite.get("max_requests_per_case"),
        )
    )
    st.markdown(f"**{story.md(C.VS_FILES_HEAD)}**")
    with st.container(key="vs-files"):
        st.table(
            pd.DataFrame(
                [
                    {
                        "file": c.item,
                        "result": c.status,
                        "recorded": c.recorded,
                        "recomputed now": c.recomputed,
                    }
                    for c in checks
                ]
            ),
            hide_index=True,
        )
    st.caption(C.VS_GATE_NOTE)
    st.markdown(f"**{story.md(C.VS_EXPECTED_HEAD)}**")
    with st.container(key="vs-expected"):
        st.table(
            pd.DataFrame(
                [
                    {"case": cid, "expected": ", ".join(sorted(_ids(c))) or "none"}
                    for cid, c in exp["cases"].items()
                ]
            ),
            hide_index=True,
        )
    st.markdown(f"**{story.md(C.VS_ATLAS_HEAD)}**")
    with st.container(key="vs-atlas"):
        st.table(
            pd.DataFrame(
                [
                    {
                        "case": c["case_id"],
                        "outcome": c.get("outcome"),
                        "TP": ", ".join(c.get("tp") or []) or "none",
                        "FP": ", ".join(c.get("fp") or []) or "none",
                        "FN": ", ".join(c.get("fn") or []) or "none",
                        "coverage gaps": ", ".join(c.get("coverage_gaps") or [])
                        or "none",
                        "source": (suite.get("atlas_sources") or {}).get(c["case_id"]),
                    }
                    for c in scores["atlas"]["cases"]
                ]
            ),
            hide_index=True,
        )
    st.markdown(f"**{story.md(C.VS_TRIALS_HEAD)}**")
    with st.container(key="vs-trials"):
        st.table(
            pd.DataFrame(
                [
                    {
                        "case": case["case_id"],
                        "trial": t.get("repetition"),
                        "status": t.get("status"),
                        "code": t.get("code") or "",
                        "violated": ", ".join(t.get("violated") or [])
                        if t.get("status") == "VALID"
                        else "",
                        "TP": len(t.get("tp") or [])
                        if t.get("status") == "VALID"
                        else "",
                        "FP": len(t.get("fp") or [])
                        if t.get("status") == "VALID"
                        else "",
                        "FN": len(t.get("fn") or [])
                        if t.get("status") == "VALID"
                        else "",
                    }
                    for case in scores["baseline"]["cases"]
                    for t in case["trials"]
                ]
            ),
            hide_index=True,
        )
    st.markdown(f"**{story.md(C.VS_TOTALS_HEAD)}**")
    with st.container(key="vs-totals"):
        rows = []
        for leg, totals in (
            (C.VS_SERIES_ATLAS, scores["atlas"]["totals"]),
            (C.VS_SERIES_MODEL, scores["baseline"]["totals"]),
        ):
            rows.append(
                {
                    "leg": leg,
                    "TP": totals["tp"],
                    "FP": totals["fp"],
                    "FN": totals["fn"],
                    "precision": f"{totals['precision']:.4f}",
                    "recall": f"{totals['recall']:.4f}",
                    "clean FP": totals["clean_false_positives"],
                }
            )
        st.table(pd.DataFrame(rows), hide_index=True)
    st.caption(C.VS_SOURCES)
