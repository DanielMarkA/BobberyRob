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
        st.markdown(
            '<img class="entry-emblem" src="/app/static/brand/emblem.webp" alt="">'
            '<div class="entry-title">Bobbery Rob</div>'
            '<div class="entry-tagline">Your identity is your greatest weapon.</div>'
            '<div class="entry-rule"></div>',
            unsafe_allow_html=True,
        )

        error = st.session_state.get("entry_error")

        # A form lets the Enter key submit, same as clicking the button.
        with st.form("entry_form", clear_on_submit=False):
            st.text_input(
                "Codename",
                key="codename_input",
                max_chars=32,  # generic safety cap only, real rules come from the backend
            )
            if error:
                st.markdown(
                    f'<div class="field-error" role="alert">{html.escape(str(error))}</div>',
                    unsafe_allow_html=True,
                )
            st.form_submit_button(
                "Enter game", type="primary", width="stretch", on_click=_submit
            )