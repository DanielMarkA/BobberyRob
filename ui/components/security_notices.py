import html

import streamlit as st


def render(notice: str) -> None:
    with st.container(key="card_notice"):
        st.markdown(
            '<div class="card-title">Security Notice</div>'
            f'<div class="card-text">{html.escape(str(notice))}</div>',
            unsafe_allow_html=True,
        )