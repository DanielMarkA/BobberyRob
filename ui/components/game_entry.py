import html

import streamlit as st

from ui.data_provider import enter_game
from ui.navigation import go_to, MISSION_BRIEFING


def _submit() -> None:
    codename = st.session_state.get("codename_input", "")
    try:
        result = enter_game(codename)
    except Exception:
        st.session_state["entry_error"] = "Could not reach the server. Please try again."
        return

    if result["ok"]:
        st.session_state["entry_error"] = None
        st.session_state["player"] = {
            "player_id": result["player_id"],
            "codename": codename.strip(),
        }
        go_to(MISSION_BRIEFING)
    else:
        st.session_state["entry_error"] = result["error"]


def render() -> None:
    with st.container(key="entry_panel"):
        st.html(
            '<div class="entry-head">'
            '<div class="entry-emblem-wrap">'
            '<div class="entry-aperture-ring" aria-hidden="true"></div>'
            '<img class="entry-emblem" src="/app/static/brand/emblem.webp" alt="">'
            "</div>"
            '<h1 class="entry-title">Bobbery Rob</h1>'
            '<p class="entry-tagline">Your identity is your greatest weapon.</p>'
            "</div>"
            '<div class="entry-rule" aria-hidden="true"></div>'
        )

        error = st.session_state.get("entry_error")

        with st.form("entry_form", clear_on_submit=False):
            st.text_input(
                "Codename",
                key="codename_input",
                max_chars=32,
                placeholder=" ",
            )
            error_html = (
                f'<div class="field-error" role="alert">{html.escape(str(error))}</div>'
                if error
                else ""
            )
            st.html(f'<div class="field-error-slot" aria-live="polite">{error_html}</div>')
            st.form_submit_button(
                "Enter game", type="primary", width="stretch", on_click=_submit
            )
