import streamlit as st

from ui.components import leaderboard, game_entry


def render() -> None:
    col_left, col_right = st.columns([554, 650], gap="large")

    with col_left:
        leaderboard.render()

    with col_right:
        game_entry.render()