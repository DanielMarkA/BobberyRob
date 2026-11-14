import streamlit as st

# Runs after the global CSS, so these rules win on screens that show the header.
_SCREEN_CSS = """
.block-container { max-width: 1500px; padding-top: 7rem; }
"""


def render() -> None:
    st.markdown(
        f"<style>{_SCREEN_CSS}</style>"
        '<div class="app-header">BOBBERY ROB</div>',
        unsafe_allow_html=True,
    )