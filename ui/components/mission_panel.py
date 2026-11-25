import html

import streamlit as st

from ui.audio import queue_sfx
from ui.components import objectives
from ui.data_provider import move_to_location, request_curator_escort, trigger_voluntary_exit


def _queue_move(target_location: str) -> None:
    st.session_state["pending_move"] = target_location


def _queue_voluntary_exit() -> None:
    st.session_state["pending_voluntary_exit"] = True


def _queue_escort() -> None:
    st.session_state["pending_escort"] = True


def process_pending() -> bool:
    """Process queued route or voluntary-exit actions after stable UI has rendered."""
    handled = False
    target = st.session_state.pop("pending_move", None)
    if target is not None:
        handled = True
        prev_loc = ((st.session_state.get("game") or {}).get("location") or {}).get("id")
        try:
            new_game = move_to_location(target)
            st.session_state["game"] = new_game
            st.session_state.pop("move_error", None)
            if (new_game.get("location") or {}).get("id") != prev_loc:
                queue_sfx("move")
            else:
                queue_sfx("item_fail")
        except Exception:
            st.session_state["move_error"] = "Could not move to that location."

    if st.session_state.pop("pending_voluntary_exit", False):
        handled = True
        try:
            st.session_state["game"] = trigger_voluntary_exit()
            st.session_state.pop("move_error", None)
        except Exception:
            st.session_state["move_error"] = "Could not complete voluntary exit."

    if st.session_state.pop("pending_escort", False):
        handled = True
        try:
            st.session_state["game"] = request_curator_escort()
            st.session_state.pop("move_error", None)
            queue_sfx("item_success")
        except Exception:
            st.session_state["move_error"] = "Could not request a curator escort."
    return handled


def render(game: dict) -> None:
    esc = html.escape

    with st.container(key="checkpoint_brief"):
        with st.expander("Mission Briefing", expanded=True):
            st.html(f'<p class="checkpoint-brief-text">{esc(game["mission_summary"])}</p>')

    location = game["location"]
    thumbnail = (
        f'<div class="checkpoint-thumbnail"><img src="{esc(location["image"])}" alt=""></div>'
        if location.get("image") else ""
    )
    st.html(
        '<section class="checkpoint-card checkpoint-location">'
        '<div class="checkpoint-card-head">'
        '<h2 class="checkpoint-heading checkpoint-icon-location">Location</h2>'
        "</div>"
        f'<p class="checkpoint-location-name">{esc(location["name"])}</p>{thumbnail}'
        "</section>"
    )

    routes = game.get("available_routes") or []
    can_exit = bool(game.get("can_voluntary_exit", False))
    can_escort = bool(game.get("can_request_escort", False))
    if routes or can_exit or can_escort:
        with st.container(key="checkpoint_routes"):
            if can_escort:
                st.button(
                    "Request Night Curator Escort (+25s)",
                    key="request_curator_escort",
                    type="primary",
                    help="Logs an official curator escort for restricted access without an invitation.",
                    on_click=_queue_escort,
                    width="stretch",
                )
            for route in routes:
                verb = "Proceed to" if route.get("is_forward") else "Return to"
                st.button(
                    f"{verb} {route['name']}",
                    key=f"move_{route['to_location']}",
                    type="primary" if route.get("is_forward") and route.get("unlocked") else "secondary",
                    disabled=not route.get("unlocked"),
                    help=route.get("reason") or None,
                    on_click=_queue_move,
                    args=(route["to_location"],),
                    width="stretch",
                )
            if can_exit:
                st.button(
                    "Accept Advisory Invite (Leave Museum)",
                    key="voluntary_exit",
                    type="secondary",
                    on_click=_queue_voluntary_exit,
                    width="stretch",
                )

    objectives.render(game["objectives"])
