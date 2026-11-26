import streamlit as st

from screens import gameplay, main_menu, mission_briefing, results
from ui.navigation import GAMEPLAY, MAIN_MENU, MISSION_BRIEFING, RESULTS, init_state
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
