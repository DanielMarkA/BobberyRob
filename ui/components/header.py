from html import escape

import streamlit as st

# Default spacing for screens with the fixed header.
_SCREEN_CSS = """
.block-container {
  max-width: 1672px;
  padding-top: calc(var(--header-h) + 2.25rem);
  padding-left: clamp(1rem, 2.4vw, 2.5rem);
  padding-right: clamp(1rem, 2.4vw, 2.5rem);
}
"""

# HTML for st.markdown must stay on one line without indentation.
_HEADER_BRAND = (
    '<img class="app-header-emblem" src="/app/static/brand/emblem.webp" alt="">'
    '<span class="app-header-title">Bobbery Rob</span>'
)


def render(*, context: str | None = None) -> None:
    label = f'<span class="app-header-context">{escape(context)}</span>' if context else ""
    st.markdown(
        f'<style>{_SCREEN_CSS}</style><div class="app-header">{_HEADER_BRAND}{label}</div>',
        unsafe_allow_html=True,
    )
