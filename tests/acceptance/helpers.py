"""Page helpers for the acceptance tests (imported by the test modules)."""

import os
import re
import time
from pathlib import Path

HASH = re.compile(r"[0-9a-f]{64}")


# -- page helpers ------------------------------------------------------------------------------
LIVE_PAGE = "/try_it_live"  # the Try It Live page (story slice 1 navigation)


def open_app(page, app) -> None:
    page.goto(app.url + LIVE_PAGE)
    page.get_by_role("button", name="Confirm & run").wait_for(timeout=60_000)


def select_project(page, name: str) -> None:
    page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
    page.locator(".st-key-claim-statement").wait_for()
    wait_idle(page)


def select_mode(page, label: str) -> None:
    page.get_by_role("radiogroup", name="Mode").get_by_role("radio", name=label).click()
    wait_idle(page)


def select_script(page, title: str) -> None:
    page.get_by_label("Fixture replies").click()
    page.get_by_role("option", name=title).click()
    wait_idle(page)


def wait_idle(page, timeout: float = 30) -> None:
    """Until Streamlit reports no script run in progress."""
    deadline = time.time() + timeout
    time.sleep(0.3)
    while time.time() < deadline:
        if page.get_by_test_id("stStatusWidget").count() == 0:
            return
        time.sleep(0.2)


def shown_hash(page, previous: str | None, timeout: float = 180) -> str:
    """The code hash in the approval panel, once it differs from `previous`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        panel = page.locator(".st-key-approval-code-hash")
        if panel.count():
            m = HASH.search(re.sub(r"\s", "", panel.inner_text()))
            if m and m.group(0) != previous:
                return m.group(0)
        time.sleep(0.3)
    raise AssertionError("no new approval request appeared")


def answer(page, typed: str) -> None:
    page.get_by_label(re.compile("Type the first 12 characters")).fill(typed)
    page.get_by_role("button", name="Submit confirmation").click()


_STARTED: dict[int, float] = {}


def click_run(page, name: str = "Confirm & run", double: bool = False) -> None:
    """Start a run from the page, remembering when, so wait_finished waits for this run."""
    _STARTED[id(page)] = time.time()
    button = page.get_by_role("button", name=name)
    button.dblclick() if double else button.click()


def wait_finished(page, app, timeout: float = 240) -> Path:
    """Until the page shows the finished run that click_run started; returns its directory."""
    since = _STARTED[id(page)] - 1
    deadline = time.time() + timeout
    while time.time() < deadline:
        new = [
            d for d in (app.runs.iterdir() if app.runs.is_dir() else [])
            if d.is_dir() and not d.name.startswith(".") and d.stat().st_ctime >= since
        ]  # fmt: skip
        label = page.locator(".st-key-results-label")
        if new and label.count():
            newest = max(new, key=lambda d: d.stat().st_ctime)
            if newest.name in label.inner_text():
                page.locator(".st-key-card-trust").wait_for(timeout=30_000)
                wait_idle(page)
                return newest
        time.sleep(0.5)
    raise AssertionError("the run did not finish on the page")


def open_step(page, n: int) -> None:
    """Expands step `n` of the Overview's story (a native expander), if it is collapsed."""
    details = page.locator(f".st-key-step-{n} details").first
    if details.get_attribute("open") is None:
        page.locator(f".st-key-step-{n} summary").first.click()
        page.wait_for_function(
            f"() => document.querySelector('.st-key-step-{n} details').open"
        )


def text(page, key: str) -> str:
    return page.locator(f".st-key-{key}").inner_text()


def table_rows(page, key: str) -> list[list[str]]:
    """Body rows of the st.table inside the keyed container, as cell texts."""
    rows = page.locator(f".st-key-{key} table tbody tr")
    return [
        [c.strip() for c in rows.nth(i).locator("td, th").all_inner_texts()]
        for i in range(rows.count())
    ]


def settle(page, timeout_ms: int = 5000) -> None:
    """Until every finite CSS animation and transition on the page has finished: the settled
    state (the HUD's first-load motion ends at 1.2 s; nothing loops). Infinite ones, such as
    Streamlit's own running indicator, are not waited for."""
    page.evaluate(
        """(ms) => Promise.race([
            Promise.all(document.getAnimations()
                .filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity)
                .map(a => a.finished.catch(() => null))),
            new Promise(r => setTimeout(r, ms))])""",
        timeout_ms,
    )


def shot(page, name: str) -> None:
    """A screenshot of the current viewport for review, if ATLAS_UI_SCREENS names a folder,
    taken in the settled state (after every finite animation; the motion frames are taken
    with page.screenshot directly)."""
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        return
    Path(folder).mkdir(parents=True, exist_ok=True)
    settle(page)
    vp = page.viewport_size or {}
    page.screenshot(
        path=str(Path(folder) / f"{name}_{vp.get('width')}x{vp.get('height')}.png")
    )


SIZES = ((1440, 900), (1280, 800), (390, 844))


def shots(page, name: str, locator=None) -> list[str]:
    """Settled viewport screenshots of one page state at 1440 x 900, 1280 x 800 and 390 x 844
    (resized in place; the sidebar is collapsed for the phone size and reopened after), with
    `locator` scrolled into view, if ATLAS_UI_SCREENS names a folder. Returns the file names."""
    folder = os.environ.get("ATLAS_UI_SCREENS")
    if not folder:
        return []
    Path(folder).mkdir(parents=True, exist_ok=True)
    names = []
    for w, h in SIZES:
        page.set_viewport_size({"width": w, "height": h})
        time.sleep(0.6)
        if w < 600:
            close = page.get_by_test_id("stSidebarCollapseButton")
            if close.count() and close.is_visible():
                close.click()
                time.sleep(0.5)
        if locator is not None:
            locator.first.scroll_into_view_if_needed()
            time.sleep(0.3)
        settle(page)
        names.append(f"{name}_{w}x{h}.png")
        page.screenshot(path=str(Path(folder) / names[-1]))
    page.set_viewport_size({"width": 1440, "height": 900})
    time.sleep(0.6)
    expand = page.get_by_test_id("stExpandSidebarButton")
    if expand.count() and expand.is_visible():
        expand.click()
        time.sleep(0.5)
    return names


FOCUSED = """() => { const e = document.activeElement; if (!e) return "none";
    const name = e.getAttribute("aria-label") || (e.innerText || e.value || "").trim()
        .split(String.fromCharCode(10))[0].slice(0, 60);
    return `${e.tagName.toLowerCase()}${e.type ? "[" + e.type + "]" : ""}: ${name}`; }"""


def tab_order(page, steps: int) -> list[str]:
    """Where keyboard focus lands, Tab by Tab, from the element focused now."""
    seen = []
    for _ in range(steps):
        page.keyboard.press("Tab")
        seen.append(page.evaluate(FOCUSED))
    return seen
