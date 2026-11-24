from html import escape

import streamlit as st

_SCREEN_CSS = """
.block-container {
  max-width: 1680px;
  padding-top: calc(var(--header-h) + 1.5rem);
  padding-left: clamp(1rem, 2.4vw, 2.5rem);
  padding-right: clamp(1rem, 2.4vw, 2.5rem);
}
"""

_HEADER_BRAND = (
    '<div class="app-header-brand">'
    '<img class="app-header-emblem" src="/app/static/brand/emblem.webp" alt="">'
    '<span class="app-header-title">Bobbery Rob</span>'
    "</div>"
)


def render(*, context: str | None = None) -> None:
    label = f'<span class="app-header-context">{escape(context)}</span>' if context else ""
    st.markdown(
        f'<style>{_SCREEN_CSS}</style><header class="app-header">{_HEADER_BRAND}{label}</header>',
        unsafe_allow_html=True,
    )
