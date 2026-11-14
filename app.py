import streamlit as st

from screens import main_menu, mission_briefing, gameplay, results
from ui.navigation import init_state, MAIN_MENU, MISSION_BRIEFING, GAMEPLAY, RESULTS

st.set_page_config(
    page_title="Bobbery Rob",
    page_icon="🕵️",
    layout="wide",
)

init_state()

# Maps each screen name to the function that draws it.
SCREENS = {
    MAIN_MENU: main_menu.render,
    MISSION_BRIEFING: mission_briefing.render,
    GAMEPLAY: gameplay.render,
    RESULTS: results.render,
}

SCREENS[st.session_state["screen"]]()