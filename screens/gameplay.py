import os

import streamlit as st

from ui.audio import render_audio_controller, track_for_gameplay
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


def _pending_status(game: dict) -> str | None:
    if st.session_state.get("pending_response"):
        speaker = game.get("dialogue", {}).get("speaker", "The guard")
        return f"{speaker} is considering your answer..."
    if st.session_state.get("pending_item"):
        return "Presenting item..."
    if st.session_state.get("pending_move"):
        return "Moving to next location..."
    if st.session_state.get("pending_voluntary_exit"):
        return "Concluding mission..."
    return None


@st.fragment
def _render_checkpoint() -> None:
    """Isolated gameplay fragment so chat/items/moves never trigger full-app reloads."""
    with st.container(key="checkpoint"):
        try:
            game = _load_state()
        except Exception:
            st.error("Could not load the game. Please try again.")
            st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
            return

        if game.get("ended"):
            go_to(RESULTS)
            st.rerun(scope="app")

        thinking_status = _pending_status(game)

        # Render all 3 columns FIRST so the scene, panels, and input stay crisp
        # and stationary (no layout shift or full-screen fade) while the LLM runs.
        # Conversation comes first in DOM for mobile and keyboard order;
        # desktop CSS maps columns to Left: Mission | Center: Scenes | Right: Status.
        conversation, status, mission = st.columns(3)
        with conversation, st.container(key="checkpoint_conversation"):
            dialogue_panel.render(game, thinking_status=thinking_status)

        with status, st.container(key="checkpoint_status"):
            suspicion_meter.render(game["suspicion"])
            inventory.render(game["inventory"])
            game_timer.render()

        with mission, st.container(key="checkpoint_mission"):
            mission_panel.render(game)

        # Execute queued backend work AFTER the stable UI has painted.
        processed = False
        if dialogue_panel.process_pending():
            processed = True
        if inventory.process_pending():
            processed = True
        if mission_panel.process_pending():
            processed = True

        if processed:
            updated = st.session_state["game"]
            if updated.get("ended"):
                go_to(RESULTS)
                st.rerun(scope="app")
            try:
                st.rerun(scope="fragment")
            except st.errors.StreamlitAPIException:
                st.rerun()

    # Sync BGM mood, one-shot event SFX, and AI guard neural speech outside the grid container
    speak_target = (
        (game["dialogue"]["speaker"], game["dialogue"]["text"], None)
        if not thinking_status
        else None
    )
    render_audio_controller(
        track=track_for_gameplay(game),
        speak_current=speak_target,
    )


def render() -> None:
    header.render(context="Active Checkpoint")
    _render_checkpoint()

    if os.getenv("BOBBERY_DEV_SHORTCUTS") == "1":
        with st.container(key="dev_shortcuts"):
            with st.expander("Dev shortcuts"):
                for ending in ("success", "compromised", "captured"):
                    st.button(f"End: {ending}", on_click=_end_mission, args=(ending,), width="stretch")
