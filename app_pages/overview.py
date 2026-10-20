"""Overview & Cases, the default page: the bundled cases as stories (`atlas.ui.story`)."""

import streamlit as st

from atlas import hosted
from atlas.ui import copy as C
from atlas.ui import story

if not hosted.enabled():
    from atlas.ui.worker import registry

    handle = registry().current()
    if handle is not None and handle.active and handle.pending() is not None:
        with st.container(key="run-waiting"):
            st.info(C.RUN_WAITING, icon=":material/pending_actions:")
            st.page_link("app_pages/try_it_live.py", label=C.RUN_WAITING_LINK)

story.overview()
