import streamlit as st

from ui.data_provider import enter_game
from ui.navigation import go_to, MISSION_BRIEFING


def render() -> None:
    with st.container(key="entry_panel"):
        st.markdown(
            '<div class="entry-mark">🕵️</div>'
            '<div class="entry-title">BOBBERY ROB</div>'
            '<div class="entry-tagline">Your identity is your greatest weapon.</div>',
            unsafe_allow_html=True,
        )

        # A form lets the Enter key submit, same as clicking the button.
        with st.form("entry_form", clear_on_submit=False):
            codename = st.text_input(
                "Choose a codename",
                placeholder="e.g. Nightfall",
                max_chars=32,  # generic safety cap only, real rules come from the backend
            )
            submitted = st.form_submit_button(
                "Enter game", type="primary", width="stretch"
            )

        if submitted:
            try:
                result = enter_game(codename)
            except Exception:
                st.error("Could not reach the server. Please try again.")
                return

            if result["ok"]:
                st.session_state["player"] = {
                    "player_id": result["player_id"],
                    "codename": codename.strip(),
                }
                go_to(MISSION_BRIEFING)
                st.rerun()
            else:
                st.error(result["error"])