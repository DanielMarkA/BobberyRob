import html
import logging

import streamlit as st

from ui.data_provider import submit_response, take_gold_urn

log = logging.getLogger(__name__)

MAX_RESPONSE_CHARS = 500  # generic safety cap only; the backend owns real limits


def _queue_send() -> None:
    """Send button callback: validate lightly, queue text, and clear input."""
    text = st.session_state.get("response_text", "").strip()
    if not text:
        st.session_state["send_error"] = "Type a response before sending."
        return
    st.session_state.pop("send_error", None)
    st.session_state["pending_response"] = text
    st.session_state["response_text"] = ""


def _queue_take_urn() -> None:
    st.session_state["pending_take_urn"] = True


def process_pending() -> bool:
    """Execute queued chat response or Take Gold Urn action after stable UI paints.

    Returns True if a pending action was processed.
    """
    handled = False

    if st.session_state.pop("pending_take_urn", False):
        handled = True
        try:
            st.session_state["game"] = take_gold_urn()
            st.session_state.pop("send_error", None)
        except Exception:
            log.exception("Taking the urn failed")
            st.session_state["send_error"] = "Could not take the Gold Urn. Please try again."

    text = st.session_state.pop("pending_response", None)
    if text is None:
        return handled

    handled = True
    try:
        st.session_state["game"] = submit_response(text)
    except Exception:
        log.exception("Failed to process player response")
        # Restore the player's text on next fragment render so they can retry.
        st.session_state["send_error"] = "Could not send your response. Please try again."
        st.session_state["_restore_response_text"] = text
    return handled


def render(game: dict, *, thinking_status: str | None = None) -> None:
    restore = st.session_state.pop("_restore_response_text", None)
    if restore is not None:
        st.session_state["response_text"] = restore

    esc = html.escape
    dialogue = game["dialogue"]
    scene = game.get("scene", {})
    artwork = "".join(
        f'<img class="checkpoint-{kind}" src="{esc(scene[kind])}" alt="">'
        for kind in ("background", "portrait")
        if scene.get(kind)
    )

    interrogation = game.get("interrogation") or {}
    personality = dialogue.get("personality")
    personality_pill = (
        f'<span class="checkpoint-personality-pill">{esc(personality)}</span>'
        if personality
        else ""
    )
    interrogation_label = interrogation.get("status_label")
    interrogation_pill = (
        f'<span class="checkpoint-interrogation-pill">{esc(interrogation_label)}</span>'
        if interrogation_label
        else ""
    )

    feedback = "".join(
        f'<p class="checkpoint-feedback{modifier}" role="{role}">{esc(message)}</p>'
        for message, modifier, role in (
            (thinking_status, "", "status"),
            (st.session_state.get("send_error"), " error", "alert"),
            (st.session_state.get("item_error"), " error", "alert"),
            (st.session_state.get("move_error"), " error", "alert"),
            (game.get("notice") if not thinking_status else None, "", "status"),
        )
        if message
    )
    st.html(
        '<section class="checkpoint-scene">'
        '<h1 class="checkpoint-sr">Security checkpoint</h1>'
        f"{artwork}"
        '<div class="checkpoint-scrim" aria-hidden="true"></div>'
        '<div class="checkpoint-dialogue">'
        '<div class="checkpoint-speaker-bar">'
        '<div class="checkpoint-speaker-left">'
        '<span class="checkpoint-live-dot" aria-hidden="true"></span>'
        f'<h2 class="checkpoint-speaker">{esc(dialogue["speaker"])}</h2>'
        f"{personality_pill}{interrogation_pill}"
        "</div>"
        '<div class="checkpoint-wave" aria-hidden="true"><span></span><span></span><span></span><span></span></div>'
        "</div>"
        '<div class="checkpoint-reply" tabindex="0" role="region" aria-label="Guard dialogue">'
        f'<p class="checkpoint-utterance">{esc(dialogue["text"])}</p>{feedback}</div>'
        "</div></section>"
    )

    if game.get("can_take_urn") and not thinking_status:
        with st.container(key="take_urn_bar"):
            st.button(
                "Take the Gold Urn",
                key="btn_take_gold_urn",
                type="primary",
                on_click=_queue_take_urn,
                width="stretch",
            )

    with st.container(key="response_bar"), st.form("response_form", border=False):
        col_input, col_send = st.columns(2, gap="small")
        with col_input:
            st.text_area(
                "Your response",
                key="response_text",
                height=64,
                max_chars=MAX_RESPONSE_CHARS,
                placeholder="Answer the guard... (Enter to send, Shift+Enter for new line)",
                label_visibility="collapsed",
            )
        with col_send:
            st.form_submit_button(
                "Send",
                type="primary",
                on_click=_queue_send,
                disabled=bool(thinking_status),
                width="stretch",
            )
