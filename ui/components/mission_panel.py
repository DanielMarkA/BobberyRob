import html

import streamlit as st

from ui.components import objectives


def render(game: dict) -> None:
    esc = html.escape

    with st.container(key="checkpoint_brief"):
        with st.expander("Mission Briefing", expanded=True):
            st.html(f'<p class="checkpoint-brief-text">{esc(game["mission_summary"])}</p>')

    location = game["location"]
    thumbnail = (
        f'<div class="checkpoint-thumbnail"><img src="{esc(location["image"])}" alt=""></div>'
        if location.get("image") else ""
    )
    st.html(
        '<section class="checkpoint-card checkpoint-location">'
        '<h2 class="checkpoint-heading checkpoint-icon-location">Current Location</h2>'
        f'<p>{esc(location["name"])}</p>{thumbnail}'
        '</section>'
    )

    objectives.render(game["objectives"])
