import logging
import os
import time

import streamlit as st

from ui import interactions
from ui.components import (
    dialogue_panel,
    game_timer,
    header,
    inventory,
    mission_panel,
    suspicion_meter,
)
from ui.data_provider import get_game_state, move_to_location, start_mission
from ui.navigation import MAIN_MENU, RESULTS, go_to, reset_mission_state

log = logging.getLogger(__name__)


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
    if st.session_state.get("pending_take_urn"):
        return "Securing the Gold Urn..."
    if st.session_state.get("pending_item"):
        return "Presenting item..."
    if st.session_state.get("pending_move"):
        return "Moving to next location..."
    if st.session_state.get("pending_voluntary_exit"):
        return "Concluding mission..."
    return None


def _rerun_fragment() -> None:
    try:
        st.rerun(scope="fragment")
    except st.errors.StreamlitAPIException:
        st.rerun()


@st.fragment(run_every=0.5)
def _advance_when_ready(target: str, ready_at: float) -> None:
    # Only mounted while cleared. Leave the last reply/empty case visible
    # without holding the Streamlit script thread during the scene change.
    if time.monotonic() < ready_at:
        return
    if (st.session_state.get("game") or {}).get("auto_advance_to") == target:
        st.session_state.pop("_advance_deadline", None)
        st.session_state["game"] = move_to_location(target)
        st.rerun(scope="app")


@st.fragment
def _render_checkpoint() -> None:
    """Isolated gameplay fragment so chat/items/moves never trigger full-app reloads."""
    with st.container(key="checkpoint"):
        try:
            game = _load_state()
        except Exception:
            log.exception("Could not load checkpoint")
            st.error("Could not load the game. Please try again.")
            st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
            return

        if game.get("ended"):
            go_to(RESULTS)
            st.rerun(scope="app")

        thinking_status = _pending_status(game)

        # Render all 3 columns FIRST so the scene, panels, and input stay crisp
        # and stationary (no layout shift or full-screen fade) while the LLM runs.
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
            if updated.get("prompt_injection_detected"):
                st.rerun(scope="app")
            _rerun_fragment()

    scene_key = f"{game['location']['id']}|{'room' if (game.get('interrogation') or {}).get('in_room') else 'floor'}|{game.get('urn_taken', False)}"
    item_tooltips = {
        item["id"]: {
            "header": item.get("inspect_header") or item["name"],
            "lines": item.get("inspect_lines") or item.get("description") or "",
        }
        for item in game.get("inventory", [])
    }
    interactions.render(scene_key, item_tooltips)

    # Auto-advance smoothly after guard clearance (or taking the Gold Urn)
    auto_target = game.get("auto_advance_to")
    if auto_target and not thinking_status and not game.get("ended"):
        scene = (game["location"]["id"], auto_target)
        pending = st.session_state.get("_advance_deadline")
        if pending is None or pending[0] != scene:
            delay = 0 if os.getenv("BOBBERY_FAST_TRANSITIONS") == "1" else 2
            pending = (scene, time.monotonic() + delay)
            st.session_state["_advance_deadline"] = pending
        _advance_when_ready(auto_target, pending[1])
    else:
        st.session_state.pop("_advance_deadline", None)


def _render_injection_jumpscare() -> None:
    """Full-impact Dishonesty jumpscare screen when prompt injection is detected."""
    with st.container(key="injection_jumpscare"):
        st.html(
            '<div class="jumpscare-flash" aria-hidden="true"></div>'
            '<div class="jumpscare-stage">'
            '  <div class="jumpscare-vignette" aria-hidden="true"></div>'
            '  <div class="jumpscare-frame">'
            '    <img class="jumpscare-portrait" src="app/static/images/dishonesty.png" alt="Dishonesty detected" />'
            "  </div>"
            '  <div class="jumpscare-copy">'
            '    <span class="jumpscare-badge">SECURITY BREACH // SYSTEM TAMPERING</span>'
            '    <h1 class="jumpscare-title">YOU GOT CAUGHT LACKING.</h1>'
            '    <p class="jumpscare-subtitle">'
            "      Prompt injection detected. You should have learned this through our lessons. "
            ""
            "    </p>"
            "  </div>"
            "</div>"
        )
        with st.container(key="jumpscare_actions"):
            col_restart, col_menu = st.columns(2)
            with col_restart:
                if st.button(
                    "Restart Game",
                    key="jumpscare_restart",
                    type="primary",
                    width="stretch",
                ):
                    start_mission()
                    reset_mission_state()
                    st.rerun()
            with col_menu:
                if st.button(
                    "Main Menu",
                    key="jumpscare_menu",
                    width="stretch",
                ):
                    start_mission()
                    reset_mission_state()
                    go_to(MAIN_MENU)
                    st.rerun()

    interactions.render("prompt_injection_jumpscare")


def render() -> None:
    try:
        game = _load_state()
    except Exception:
        log.exception("Could not load gameplay")
        st.error("Could not load the game. Please try again.")
        st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
        return
    if game.get("prompt_injection_detected"):
        _render_injection_jumpscare()
        return

    header.render(context="Active Checkpoint")
    _render_checkpoint()

    with st.container(key="checkpoint_actions"):
        col_restart, col_menu = st.columns(2)
        with col_restart:
            if st.button("Restart Mission", key="cp_restart", width="stretch"):
                start_mission()
                reset_mission_state()
                st.rerun()
        with col_menu:
            if st.button("Main Menu", key="cp_main_menu", width="stretch"):
                go_to(MAIN_MENU)
                st.rerun()

    if os.getenv("BOBBERY_DEV_SHORTCUTS") == "1":
        with st.container(key="dev_shortcuts"), st.expander("Dev shortcuts"):
            for ending in ("success", "compromised", "captured"):
                st.button(f"End: {ending}", on_click=_end_mission, args=(ending,), width="stretch")
