import streamlit as st

from ui.components import header, mission_panel
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
        game = _load_state()
    except Exception:
        st.error("Could not load the game. Please try again.")
        st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
        return

    col_left, col_center, col_right = st.columns([342, 914, 343], gap="medium")

    with col_left:
        mission_panel.render(game)

    with col_center:
        with st.container(key="card_scene_placeholder"):
            st.caption("Center panel: built in Milestone 4.2")

    with col_right:
        with st.container(key="card_status_placeholder"):
            st.caption("Right panel: built in Milestone 4.3")

    # Temporary dev shortcut, removed once the real ending flow exists
    st.button("End Mission (temporary)", on_click=go_to, args=(RESULTS,))