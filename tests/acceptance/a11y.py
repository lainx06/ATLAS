"""Accessibility helpers for the acceptance tests (slice 3, part E): axe-core (the dev-only
`axe-playwright-python` package bundles axe-core 4.12.1, MPL-2.0) run against a page, and each
violating node classified as ATLAS's own markup or Streamlit's.

ATLAS markup is the HTML ATLAS writes itself: anything inside an element whose class starts
with `hud` (the HUD, the story's markup, the comparison chart, the limits page) and the content
of a Markdown block ATLAS authored (`stMarkdownContainer`). Colour contrast on any element is
counted as ATLAS's too, because the theme's colour tokens are ATLAS's choice. Everything else
(navigation, widget chrome, the toolbar) is Streamlit's markup: recorded, not patched.
"""

import json
from pathlib import Path

from axe_playwright_python.sync_playwright import Axe

SERIOUS = ("serious", "critical")
_AXE = Axe()

CLASSIFY = """(selector) => {
  let el = null;
  try { el = document.querySelector(selector); } catch (e) { return "unknown"; }
  if (!el) return "unknown";
  if (el.closest('[class^="hud"], [class*=" hud"]')) return "atlas";
  if (el.closest('[data-testid="stMarkdownContainer"]')) return "atlas";
  return "streamlit";
}"""


def run(page) -> dict:
    """axe-core's full result for the page as it is now."""
    return _AXE.run(page).response


def classify(page, response: dict) -> list[dict]:
    """Every serious or critical violation node, with its owner ("atlas" or "streamlit")."""
    out = []
    for v in response.get("violations") or []:
        if v.get("impact") not in SERIOUS:
            continue
        for node in v.get("nodes") or []:
            target = node.get("target") or []
            selector = target[-1] if target and isinstance(target[-1], str) else ""
            owner = page.evaluate(CLASSIFY, selector) if selector else "unknown"
            if v["id"] == "color-contrast":
                owner = "atlas"
            out.append(
                {
                    "rule": v["id"],
                    "impact": v.get("impact"),
                    "owner": owner,
                    "target": target,
                    "html": (node.get("html") or "")[:300],
                    "summary": (node.get("failureSummary") or "")[:300],
                }
            )
    return out


def save(folder: Path, name: str, response: dict, nodes: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.axe.json").write_text(
        json.dumps(
            {"violations": response.get("violations"), "serious": nodes}, indent=1
        ),
        encoding="utf-8",
    )


# -- keyboard focus ----------------------------------------------------------------------------
FOCUSED = """() => {
  const e = document.activeElement;
  if (!e || e === document.body) return null;
  const name = (e.getAttribute('aria-label') || e.innerText || e.value || e.tagName)
    .trim().split(String.fromCharCode(10))[0].slice(0, 60);
  let node = e, shown = null;
  for (let i = 0; i < 7 && node && node !== document.body; i++, node = node.parentElement) {
    const cs = getComputedStyle(node), r = node.getBoundingClientRect();
    const visible = r.width > 4 && r.height > 4 && parseFloat(cs.opacity) > 0;
    const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
    const shadow = cs.boxShadow && cs.boxShadow !== 'none';
    if (visible && (outline || shadow)) { shown = i; break; }
  }
  const testid = e.closest('[data-testid]');
  return {tag: e.tagName.toLowerCase(), name, shown,
          testid: testid ? testid.getAttribute('data-testid') : ''};
}"""


def tab_walk(
    page, steps: int = 60, shots: Path | None = None, name: str = ""
) -> list[dict]:
    """Tab from the top of the page until focus returns to the first element (or `steps`),
    recording each focused element and whether a visible focus indicator is drawn on it or a
    near ancestor; optionally a screenshot per step."""
    page.evaluate("() => { document.activeElement && document.activeElement.blur(); }")
    seen: list[dict] = []
    for i in range(steps):
        page.keyboard.press("Tab")
        page.wait_for_timeout(120)
        info = page.evaluate(FOCUSED)
        if info is None:
            continue
        if seen and (info["tag"], info["name"]) == (seen[0]["tag"], seen[0]["name"]):
            break
        seen.append(info)
        if shots is not None:
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"tab_{name}_{len(seen):02d}.png"))
    return seen


# ATLAS's charts and diagrams (SVG, and the limits page's figure): role="img" and a name.
SVGS = r"""() => [...document.querySelectorAll('[data-testid="stMain"] svg, [data-testid="stMain"] figure')]
  .filter(s => s.closest('[class^="hud"], [class*=" hud"]')
               && !s.closest('[data-testid="stIconMaterial"]') && !s.closest('button')
               && s.getAttribute('aria-hidden') !== 'true' && !s.closest('[aria-hidden="true"]'))
  .map(s => {
    const lab = (s.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)
      .map(id => (document.getElementById(id) || {}).textContent || '').join(' ').trim();
    const title = s.querySelector(':scope > title');
    return {tag: s.tagName.toLowerCase(), role: s.getAttribute('role'),
            name: (s.getAttribute('aria-label') || lab || (title && title.textContent) || '').trim(),
            cls: (s.getAttribute('class') || '').toString().slice(0, 40)};
  })"""
