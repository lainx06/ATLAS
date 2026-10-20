"""How It Works & Limits: a placeholder until slice 2 (no content is invented here)."""

import streamlit as st

from atlas.ui import copy as C

with st.container(key="hud-page"):
    st.title(C.PAGE_LIMITS)
    with st.container(key="placeholder"):
        st.markdown(C.PLACEHOLDER)
