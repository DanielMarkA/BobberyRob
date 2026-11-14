import html

import streamlit as st

from ui.components import header
from ui.data_provider import get_mission_result
from ui.formatting import format_penalty, format_time_precise
from ui.navigation import go_to, MAIN_MENU, MISSION_BRIEFING


def _row(label: str, value: str, extra: str = "") -> str:
    return (
        f'<div class="result-row{extra}">'
        f"<span>{html.escape(label)}</span>"
        f'<span class="v">{html.escape(value)}</span>'
        "</div>"
    )


def _time(seconds) -> str:
    return format_time_precise(seconds) if seconds is not None else "—"


def render() -> None:
    header.render()

    try:
        r = get_mission_result()
    except Exception:
        st.error("Could not load your results. Please try again.")
        st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
        return

    esc = html.escape

    if r["penalties"]:
        penalty_rows = "".join(
            _row(p["label"], format_penalty(p["seconds"])) for p in r["penalties"]
        )
    else:
        penalty_rows = _row("Penalties", "None")

    note = "" if r["adjusted_seconds"] is not None else (
        '<div class="result-note">Failed attempts are not ranked.</div>'
    )
    badge = '<span class="pb-badge">New Record!</span>' if r["is_new_record"] else ""

    col_left, col_right = st.columns([660, 854], gap="large")

    with col_left:
        st.markdown(
            '<div class="result-scene">'
            '<div class="scene-art">'
            '<div class="img-slot-label">Mission result image</div>'
            f'<div class="img-slot-caption">{esc(r["scene_caption"])}</div>'
            "</div>"
            f'<div class="result-quote">“{esc(r["quote"])}”'
            f'<small>— {esc(r["quote_by"])}</small></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown(
            f'<div class="result-heading">{esc(r["heading"])}</div>'
            f'<div class="result-banner {esc(r["tone"])}">{esc(r["outcome_label"])}</div>'
            '<div class="result-label">Adjusted completion time</div>'
            f'<div class="result-time">{_time(r["adjusted_seconds"])}</div>'
            + note
            + _row("Raw Gameplay Time", _time(r["raw_seconds"]))
            + penalty_rows
            + _row("Adjusted Time", _time(r["adjusted_seconds"]), " total")
            + _row("Final Suspicion", f'{r["final_suspicion"]} / 100')
            + _row("Objectives Completed", f'{r["objectives_done"]} / {r["objectives_total"]}')
            + '<div class="pb-panel"><div class="pb-label">Personal best</div>'
            f'<div class="pb-row"><span class="pb-time">{_time(r["personal_best_seconds"])}</span>'
            f"{badge}</div></div>",
            unsafe_allow_html=True,
        )

    with st.container(key="result_actions"):
        _, mid, _ = st.columns([1, 3, 1])
        with mid:
            col_retry, col_menu = st.columns(2, gap="medium")
            with col_retry:
                st.button("TRY AGAIN", on_click=go_to, args=(MISSION_BRIEFING,), width="stretch")
            with col_menu:
                st.button("MAIN MENU", type="primary", on_click=go_to, args=(MAIN_MENU,), width="stretch")