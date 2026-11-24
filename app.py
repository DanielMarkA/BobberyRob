from pathlib import Path

import streamlit as st

from screens import main_menu, mission_briefing, gameplay, results
from ui.navigation import init_state, MAIN_MENU, MISSION_BRIEFING, GAMEPLAY, RESULTS
from ui.styles import inject_global_styles

st.set_page_config(
    page_title="Bobbery Rob",
    page_icon="static/brand/emblem.webp",
    layout="wide",
)

inject_global_styles()
init_state()

SCREENS = {
    MAIN_MENU: main_menu.render,
    MISSION_BRIEFING: mission_briefing.render,
    GAMEPLAY: gameplay.render,
    RESULTS: results.render,
}

SCREENS[st.session_state["screen"]]()
