import streamlit as st

from ui.components import (
    dialogue_panel, header, inventory, mission_panel,
    security_notices, suspicion_meter,
)
from ui.data_provider import get_game_state
from ui.navigation import go_to, MAIN_MENU, RESULTS


def _load_state() -> dict:
    """Load the game state once per mission, then reuse it across reruns."""
    if "game" not in st.session_state:
        st.session_state["game"] = get_game_state()
    return st.session_state["game"]


def render() -> None:
    header.render()

    try:
        _load_state()
    except Exception:
        st.error("Could not load the game. Please try again.")
        st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
        return

    # Send any queued response to the backend FIRST, so all panels show new state.
    dialogue_panel.process_pending()
    inventory.process_pending()
    game = st.session_state["game"]

    col_left, col_center, col_right = st.columns([342, 914, 343], gap="medium")

    with col_left:
        mission_panel.render(game)

    with col_center:
        dialogue_panel.render(game)

    with col_right:
        suspicion_meter.render(game["suspicion"])
        inventory.render(game["inventory"])
        security_notices.render(game["notice"])

    # Temporary dev shortcut, removed once the real ending flow exists
    st.button("End Mission (temporary)", on_click=go_to, args=(RESULTS,))