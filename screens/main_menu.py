import streamlit as st

from ui.audio import render_audio_controller
from ui.components import leaderboard, game_entry

def render() -> None:
    render_audio_controller(track="menu")
    with st.container(key="main_menu"):
        # The primary task comes first in reading and keyboard order.
        entry, rankings = st.columns(2)
        with entry:
            game_entry.render()
        with rankings:
            leaderboard.render()
