"""The How It Works & Limits page (UI restructure slice 2, part C).

Fixed copy only (`atlas.ui.copy`), sourced from README.md, docs/SPEC.md and
docs/HOSTED_OPERATIONS.md; Expert view cites each item's section and shows the README's
"Limitations" in their original wording (read from README.md itself, so the two cannot drift;
a test checks that every README item has its plain counterpart). The five-step diagram is
static: no number, and no motion beyond one fade the first time it is shown in a session
(never under reduced motion).
"""

import re
from pathlib import Path

import streamlit as st

from atlas.ui import copy as C
from atlas.ui import hud as H
from atlas.ui import story
from atlas.ui.catalogue import ROOT

README = ROOT / "README.md"
PLAYED = "limits_diagram_played"  # session key: the diagram's fade has played

CSS = """
<style>
.st-key-lim-head { gap: 8px 16px; align-items: flex-start; flex-wrap: wrap; }
.st-key-lim-head h1 { padding: 0 0 0.5rem; }
.hud-lim-diagram { margin: 4px 0 8px; }
.hud-lim-diagram .hud-lbl { display: block; margin-bottom: 6px; }
.hud-lim-diagram ol { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap;
  gap: 8px 0; align-items: stretch; }
.hud-lim-diagram li { display: flex; align-items: center; }
.hud-lim-diagram .lim-box { background: #0F1720; border: 1px solid #1E2A36; border-radius: 4px;
  padding: 8px 12px; font-size: 13px; line-height: 1.35; color: #E2E8F0; min-width: 7.5rem;
  max-width: 11rem; }
.hud-lim-diagram li.lim-ai .lim-box { border-style: dashed; border-color: #A8A29E; }
.hud-lim-diagram li.lim-check .lim-box { border-color: #67E8F9; }
.hud-lim-diagram .lim-arrow { color: #94A3B8; padding: 0 8px; }
@media (prefers-reduced-motion: no-preference) {
  @keyframes lim-fade { from { opacity: 0; } }
  .hud-lim-diagram.lim-fade { animation: lim-fade 400ms ease-out 1; }
}
.hud-lim ol, .hud-lim ul { margin: 4px 0 0; padding-left: 20px; }
.hud-lim li { margin: 0 0 8px; font-size: 16px; line-height: 1.5; color: #E2E8F0; }
.hud-lim .lim-title { font-weight: 600; }
.hud-lim .hud-src { margin-top: 2px; }
.hud-lim .lim-orig { color: #94A3B8; font-size: 13px; margin-top: 2px; }
.hud-lim code { font-size: 12px; }
</style>
"""


def readme_limitations(text: str | None = None) -> list[str]:
    """The README's "## Limitations" bullets, in order (each item one line)."""
    if text is None:
        text = README.read_text(encoding="utf-8")
    m = re.search(r"^## Limitations\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE)
    if not m:
        return []
    return [
        line[2:].strip() for line in m.group(1).splitlines() if line.startswith("- ")
    ]


def diagram(*, fade: bool) -> str:
    """The five steps, in order, as boxes with arrows (wraps at narrow widths)."""
    kinds = ("", "lim-check", "lim-ai", "", "lim-check")
    items = []
    for i, (name, kind) in enumerate(zip(C.HOW_DIAGRAM_SHORT, kinds, strict=True)):
        arrow = (
            '<span class="lim-arrow" aria-hidden="true">→</span>'
            if i < len(C.HOW_DIAGRAM_SHORT) - 1
            else ""
        )
        items.append(
            f'<li class="{kind}"><span class="lim-box">{H.esc(name)}</span>{arrow}</li>'
        )
    return (
        f'<figure class="hud hud-lim-diagram{" lim-fade" if fade else ""}" role="img" '
        f'aria-label="{H.esc(C.HOW_DIAGRAM_ALT)}">'
        f'<span class="hud-lbl">{H.esc(C.DIAGRAM_LABEL)}</span>'
        f"<ol>{''.join(items)}</ol></figure>"
    )


def _items(entries: list[tuple[str, ...]], plain: bool, *, ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    out = []
    for entry in entries:
        if len(entry) == 3:  # (title, text, source)
            title, text, source = entry
            html = f'<span class="lim-title">{H.esc(title)}.</span> {story.code_html(text)}'
        else:  # (text, source)
            text, source = entry
            html = story.code_html(text)
        if not plain:
            html += (
                f'<div class="hud-src">{H.esc(C.SOURCE_LABEL)}: {H.esc(source)}</div>'
            )
        out.append(f"<li>{html}</li>")
    return f'<div class="hud hud-lim"><{tag}>{"".join(out)}</{tag}></div>'


def limits_html(plain: bool, original: list[str]) -> str:
    out = []
    for i, text in enumerate(C.LIMITS_PLAIN):
        html = story.code_html(text)
        if not plain and i < len(original):
            html += f'<div class="lim-orig">{story.code_html(original[i])}</div>'
        out.append(f"<li>{html}</li>")
    return f'<div class="hud hud-lim"><ul>{"".join(out)}</ul></div>'


def page(readme: Path | None = None) -> None:
    readme = Path(readme or README)
    st.html(CSS)
    plain = not story.expert()
    with st.container(key="lim-page"):
        with st.container(key="lim-head", horizontal=True):
            st.title(C.PAGE_LIMITS)
            story.expert_toggle()
        st.subheader(C.HOW_HEAD)
        st.caption(story.md(C.HOW_INTRO))
        fade = not st.session_state.get(PLAYED, False)
        with st.container(key="lim-diagram"):
            st.markdown(diagram(fade=fade), unsafe_allow_html=True)
        st.session_state[PLAYED] = True
        if plain:
            plain_body(readme)
            return
        with st.container(key="lim-steps"):
            st.markdown(
                _items(list(C.HOW_STEPS), plain, ordered=True), unsafe_allow_html=True
            )
        st.subheader(C.SAFETY_HEAD)
        with st.container(key="lim-safety"):
            st.markdown(
                _items(list(C.SAFETY), plain, ordered=False), unsafe_allow_html=True
            )
        st.subheader(C.LIMITS_HEAD)
        st.caption(story.md(C.LIMITS_INTRO))
        original = readme_limitations(Path(readme).read_text(encoding="utf-8"))
        with st.container(key="lim-limits"):
            st.markdown(limits_html(plain, original), unsafe_allow_html=True)
        if not plain:
            with st.container(key="lim-limits-source"):
                st.caption(f"{C.SOURCE_LABEL}: {C.LIMITS_SOURCE}")
        st.subheader(C.NOT_DO_HEAD)
        with st.container(key="lim-not-do"):
            st.markdown(
                _items(list(C.NOT_DO), plain, ordered=False), unsafe_allow_html=True
            )


def how_lines() -> list[tuple[str, str, str]]:
    """H1: each step's short title (the diagram's) with its one line; the longer titles and
    text are in Expert view."""
    return [
        (title, line, source)
        for title, line, (_title, _text, source) in zip(
            C.HOW_DIAGRAM_SHORT, C.HOW_LINES, C.HOW_STEPS, strict=True
        )
    ]


def plain_body(readme: Path) -> None:
    """Plain view (readability pass): the five steps in one line each, six safety tiles,
    the four key limits, and every limitation in full behind one click."""
    with st.container(key="lim-steps"):
        st.markdown(_items(how_lines(), True, ordered=True), unsafe_allow_html=True)
    st.subheader(C.SAFETY_HEAD)
    with st.container(key="lim-safety-tiles"):
        tiles = list(C.SAFETY_TILES)
        for start in range(0, len(tiles), 3):
            for col, (title, line) in zip(
                st.columns(3), tiles[start : start + 3], strict=True
            ):
                with col, st.container(border=True, height="stretch"):
                    st.markdown(f"**{story.md(title)}**")
                    st.markdown(story.md(line))
    st.subheader(C.KEY_LIMITS_HEAD)
    with st.container(key="lim-key-limits"):
        st.markdown(
            '<div class="hud hud-lim"><ul>'
            + "".join(f"<li>{story.code_html(x)}</li>" for x in C.KEY_LIMITS)
            + "</ul></div>",
            unsafe_allow_html=True,
        )
    original = readme_limitations(Path(readme).read_text(encoding="utf-8"))
    with st.expander(C.ALL_LIMITS.format(n=len(C.LIMITS_PLAIN)), key="lim-all-limits"):
        st.caption(story.md(C.LIMITS_INTRO))
        with st.container(key="lim-limits"):
            st.markdown(limits_html(True, original), unsafe_allow_html=True)
        st.subheader(C.NOT_DO_HEAD)
        with st.container(key="lim-not-do"):
            st.markdown(
                _items(list(C.NOT_DO), True, ordered=False), unsafe_allow_html=True
            )
