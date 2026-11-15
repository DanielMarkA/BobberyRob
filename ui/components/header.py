import streamlit as st

# Runs after the global CSS, so these rules win on screens that show the header.
# Content starts below the fixed header (Figma: gameplay content begins ~36px under it).
_SCREEN_CSS = """
.block-container {
  max-width: 1672px;
  padding-top: calc(var(--header-h) + 2.25rem);
  padding-left: clamp(1rem, 2.4vw, 2.5rem);
  padding-right: clamp(1rem, 2.4vw, 2.5rem);
}
"""

# HTML for st.markdown must stay on one line without indentation.
_HEADER_HTML = (
    '<div class="app-header">'
    '<img class="app-header-emblem" src="/app/static/brand/emblem.webp" alt="">'
    '<span class="app-header-title">Bobbery Rob</span>'
    "</div>"
)


def render() -> None:
    st.markdown(f"<style>{_SCREEN_CSS}</style>{_HEADER_HTML}", unsafe_allow_html=True)