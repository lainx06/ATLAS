"""ATLAS browser UI (T-07). Run: uv run --locked streamlit run app.py

Four pages in Streamlit's native multipage navigation (UI restructure slice 1,
docs/UI_DESIGN_HUD.md §12): Overview & Cases (the default: the bundled recorded runs told as
cases), Try It Live (hosted: the one live session per visitor; local: run a project or open a
recorded run), AI Agent vs. Model Alone (the T-11 comparison, gated on its recorded result
hashes) and How It Works & Limits (slice 2). Every result shown is read from the run's files
and passes the verification gate (`atlas.ui.results.gate`) first.
"""

import streamlit as st

from atlas import hosted
from atlas.ui import copy as C
from atlas.ui import views as V

st.set_page_config(page_title="ATLAS", page_icon=":material/fact_check:", layout="wide")
V.inject_css()

PAGES = [
    st.Page(
        "app_pages/overview.py",
        title=C.PAGE_OVERVIEW,
        icon=":material/fact_check:",
        default=True,
    ),
    st.Page(
        "app_pages/try_it_live.py",
        title=C.PAGE_LIVE,
        icon=":material/play_circle:",
    ),
    st.Page(
        "app_pages/agent_vs_model.py",
        title=C.PAGE_AGENT,
        icon=":material/compare_arrows:",
    ),
    st.Page(
        "app_pages/how_it_works.py",
        title=C.PAGE_LIMITS,
        icon=":material/info:",
    ),
]
page = st.navigation(PAGES, position="top")

# Hosted mode (T-12), selected only by ATLAS_HOSTED=1: the bundled cases and one live session
# per visitor session; nothing local (runs, Docker, approvals) is reached.
if hosted.enabled():
    from atlas.hosted import page as hosted_page

    hosted_page.sidebar()

page.run()
