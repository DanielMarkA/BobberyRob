import os

import streamlit as st

from ui.components import (
    dialogue_panel, game_timer, header, inventory, mission_panel, suspicion_meter,
)
from ui.data_provider import get_game_state
from ui.navigation import go_to, MAIN_MENU, RESULTS


def _load_state() -> dict:
    """Load the game state once per mission, then reuse it across reruns."""
    if "game" not in st.session_state:
        st.session_state["game"] = get_game_state()
    return st.session_state["game"]


def _end_mission(ending: str) -> None:
    """TEMPORARY dev shortcut. The real ending will come from the backend."""
    st.session_state["_mock_ending"] = ending
    go_to(RESULTS)


def render() -> None:
    header.render(context="Active Checkpoint")

    with st.container(key="checkpoint"):
        try:
            _load_state()
        except Exception:
            st.error("Could not load the game. Please try again.")
            st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
            return

        # Send queued actions before drawing, so every panel sees the new state.
        dialogue_panel.process_pending()
        inventory.process_pending()
        game = st.session_state["game"]

        # Conversation comes first in DOM for mobile and keyboard order;
        # desktop CSS maps columns to Left: Mission | Center: Scenes | Right: Status.
        conversation, status, mission = st.columns(3)
        with conversation, st.container(key="checkpoint_conversation"):
            dialogue_panel.render(game)

        with status, st.container(key="checkpoint_status"):
            suspicion_meter.render(game["suspicion"])
            inventory.render(game["inventory"])
            game_timer.render()

        with mission, st.container(key="checkpoint_mission"):
            mission_panel.render(game)

    if os.getenv("BOBBERY_DEV_SHORTCUTS") == "1":
        with st.container(key="dev_shortcuts"):
            with st.expander("Dev shortcuts"):
                for ending in ("success", "compromised", "captured"):
                    st.button(f"End: {ending}", on_click=_end_mission, args=(ending,), width="stretch")
