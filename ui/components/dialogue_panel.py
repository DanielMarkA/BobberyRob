import html

import streamlit as st

from ui.data_provider import submit_response

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


def process_pending() -> bool:
    """Execute a queued chat response after stable UI has rendered.

    Returns True if a pending response was processed.
    """
    text = st.session_state.pop("pending_response", None)
    if text is None:
        return False

    try:
        st.session_state["game"] = submit_response(text)
    except Exception:
        # Restore the player's text on next fragment render so they can retry.
        st.session_state["send_error"] = "Could not send your response. Please try again."
        st.session_state["_restore_response_text"] = text
    return True


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
    evidence_quotes = interrogation.get("evidence_quotes") or []
    evidence_note = (
        f'On record: "{evidence_quotes[0]}"' if evidence_quotes else None
    )

    feedback = "".join(
        f'<p class="checkpoint-feedback{modifier}" role="{role}">{esc(message)}</p>'
        for message, modifier, role in (
            (thinking_status, "", "status"),
            (st.session_state.get("send_error"), " error", "alert"),
            (st.session_state.get("item_error"), " error", "alert"),
            (st.session_state.get("move_error"), " error", "alert"),
            (evidence_note, "", "status"),
            (game.get("notice") if not thinking_status else None, "", "status"),
        )
        if message
    )
    st.html(
        '<section class="checkpoint-scene">'
        '<h1 class="checkpoint-sr">Security checkpoint</h1>'
        f'{artwork}'
        '<div class="checkpoint-scrim" aria-hidden="true"></div>'
        '<div class="checkpoint-dialogue">'
        '<div class="checkpoint-speaker-bar">'
        '<div class="checkpoint-speaker-left">'
        '<span class="checkpoint-live-dot" aria-hidden="true"></span>'
        f'<h2 class="checkpoint-speaker">{esc(dialogue["speaker"])}</h2>'
        "</div>"
        '<div class="checkpoint-wave" aria-hidden="true"><span></span><span></span><span></span><span></span></div>'
        "</div>"
        '<div class="checkpoint-reply" tabindex="0" role="region" aria-label="Guard dialogue">'
        f'<p class="checkpoint-utterance">{esc(dialogue["text"])}</p>{feedback}</div>'
        "</div></section>"
    )

    with st.container(key="response_bar"):
        with st.form("response_form", border=False):
            col_input, col_send = st.columns(2, gap="small")
            with col_input:
                st.text_area(
                    "Your response",
                    key="response_text",
                    height=64,
                    max_chars=MAX_RESPONSE_CHARS,
                    placeholder="Answer the guard in your own words...",
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
