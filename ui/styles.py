"""Global styles for Bobbery Rob. The CSS itself lives in ui/styles.css."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).with_name("styles.css")


@st.cache_data(max_entries=4)
def _read_css(path: str, mtime_ns: int) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def inject_global_styles() -> None:
    """Call once per run, right after st.set_page_config()."""
    try:
        mtime_ns = _CSS_PATH.stat().st_mtime_ns
    except OSError:
        return  # missing stylesheet: the app still works, just unstyled
    css = _read_css(str(_CSS_PATH), mtime_ns)
    if not css:
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
