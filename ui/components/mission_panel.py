import html

import streamlit as st

from ui.components import objectives
from ui.components.image_slot import image_slot


def render(game: dict) -> None:
    esc = html.escape

    with st.container(key="card_briefing"):
        with st.expander("Mission Briefing", expanded=True):
            st.markdown(
                f'<div class="card-text">{esc(game["mission_summary"])}</div>',
                unsafe_allow_html=True,
            )

    with st.container(key="card_location"):
        st.markdown(
            '<div class="card-title">Current Location</div>'
            f'<div class="card-sub">{esc(game["location"]["name"])}</div>',
            unsafe_allow_html=True,
        )
        image_slot("Location image", ratio="340 / 159")

    objectives.render(game["objectives"])