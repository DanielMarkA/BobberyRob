import html

import streamlit as st

from ui.data_provider import submit_response

MAX_RESPONSE_CHARS = 500  # generic safety cap only; the backend owns real limits


def _queue_send() -> None:
    """Send button callback: validate lightly and queue the text."""
    text = st.session_state.get("response_text", "").strip()
    if not text:
        st.session_state["send_error"] = "Type a response before sending."
        return
    st.session_state.pop("send_error", None)
    st.session_state["pending_response"] = text


def process_pending() -> None:
    """Call BEFORE drawing any panel, so every panel sees the updated state."""
    text = st.session_state.pop("pending_response", None)
    if text is None:
        return

    with st.spinner("The guard is considering your answer..."):
        try:
            st.session_state["game"] = submit_response(text)
        except Exception:
            # Keep the player's text so they can retry without retyping.
            st.session_state["send_error"] = "Could not send your response. Please try again."
            return

    st.session_state["response_text"] = ""  # clear the input only on success


def render(game: dict) -> None:
    esc = html.escape
    dialogue = game["dialogue"]

    with st.container(key="card_scene"):
        st.markdown(
            '<div class="scene">'
            '<div class="scene-art">'
            '<div class="img-slot-label">Security guard / museum scene</div>'
            '<div class="img-slot-caption">Scene artwork placeholder</div>'
            "</div>"
            '<div class="dialogue-wrap">'
            f'<div class="speaker">{esc(dialogue["speaker"])}</div>'
            f'<div class="dialogue-text">{esc(dialogue["text"])}</div>'
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with st.container(key="response_bar"):
        with st.form("response_form", border=False):
            col_input, col_send = st.columns([764, 112], gap="small")
            with col_input:
                st.text_area(
                    "Your response",
                    key="response_text",
                    height=96,
                    max_chars=MAX_RESPONSE_CHARS,
                    placeholder="Type your response here...",
                    label_visibility="collapsed",
                )
            with col_send:
                st.form_submit_button(
                    "Send", type="primary", on_click=_queue_send, width="stretch"
                )

        if "send_error" in st.session_state:
            st.error(st.session_state["send_error"])