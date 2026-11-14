import html

import streamlit as st


def render(items: list[dict]) -> None:
    with st.container(key="card_objectives"):
        st.markdown('<div class="card-title">Objectives</div>', unsafe_allow_html=True)

        if not items:
            st.markdown('<div class="card-text">No objectives yet.</div>', unsafe_allow_html=True)
            return

        rows = "".join(
            f'<div class="obj{" done" if o["done"] else ""}">'
            f'<span class="obj-box">{"☑" if o["done"] else "☐"}</span>'
            f'<span>{html.escape(o["text"])}</span>'
            f"</div>"
            for o in items
        )
        st.markdown(rows, unsafe_allow_html=True)