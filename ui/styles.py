"""Global styles for Bobbery Rob. The CSS itself lives in ui/styles.css."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).with_name("styles.css")

def inject_global_styles() -> None:
    """Call once per run, right after st.set_page_config()."""
    try:
        css = _CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return  # missing stylesheet: the app still works, just unstyled
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)