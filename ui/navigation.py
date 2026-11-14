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


def init_state() -> None:
    """Create navigation defaults the first time the app loads."""
    st.session_state.setdefault("screen", MAIN_MENU)


def go_to(screen: str) -> None:
    """Switch to another screen. Meant to be used as a button on_click callback."""
    st.session_state["screen"] = screen