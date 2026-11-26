"""Navigation state for the frontend.

This module only tracks WHICH screen is visible.
It must never hold game rules, suspicion, timers, or inventory.
"""

import streamlit as st

# Screen names (single source of truth: use these constants, not raw strings)
MAIN_MENU = "main_menu"
MISSION_BRIEFING = "mission_briefing"
GAMEPLAY = "gameplay"
RESULTS = "results"


# Everything that belongs to ONE mission run. Cleared when a new mission starts.
_MISSION_KEYS = (
    "_advance_deadline",
    "game",
    "selected_item",
    "response_text",
    "send_error",
    "item_error",
    "move_error",
    "pending_response",
    "pending_item",
    "pending_move",
    "pending_take_urn",
    "pending_voluntary_exit",
    "pending_escort",
)


def reset_mission_state() -> None:
    for key in _MISSION_KEYS:
        st.session_state.pop(key, None)


def init_state() -> None:
    """Create navigation defaults the first time the app loads."""
    st.session_state.setdefault("screen", MAIN_MENU)


def go_to(screen: str) -> None:
    """Switch to another screen. Meant to be used as a button on_click callback."""
    st.session_state["screen"] = screen
