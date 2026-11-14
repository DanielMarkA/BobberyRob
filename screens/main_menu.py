import streamlit as st

from ui.components import leaderboard
from ui.navigation import go_to, MISSION_BRIEFING


def render() -> None:
    col_left, col_right = st.columns([554, 650], gap="large")

    with col_left:
        leaderboard.render()

    with col_right:
        with st.container(key="entry_panel"):
            st.title("Bobbery Rob")
            st.caption("Entry panel (placeholder, built in 2.2)")
            st.button("Enter Game", on_click=go_to, args=(MISSION_BRIEFING,))