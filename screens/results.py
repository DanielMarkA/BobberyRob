import html

import streamlit as st

from ui.audio import render_audio_controller, track_for_result
from ui.components import header
from ui.data_provider import get_mission_result
from ui.formatting import format_penalty, format_time_precise
from ui.navigation import go_to, MAIN_MENU, MISSION_BRIEFING


def _row(label: str, value: str, icon: str, modifier: str = "") -> str:
    cls = f"result-row {modifier}".strip()
    return (
        f'<div class="{cls}">'
        f'<dt class="result-icon-{icon}">{html.escape(label)}</dt>'
        f"<dd>{html.escape(value)}</dd>"
        "</div>"
    )


def _time(seconds) -> str:
    return format_time_precise(seconds) if seconds is not None else "—"


def _summary(result: dict, tone: str) -> None:
    esc = html.escape
    penalty_rows = "".join(
        _row(penalty["label"], format_penalty(penalty["seconds"]), "timer", "penalty")
        for penalty in result["penalties"]
    ) or _row("Penalties", "None", "timer")
    is_ranked = result["adjusted_seconds"] is not None
    note = "" if is_ranked else (
        '<p class="result-note">Failed attempts are not ranked.</p>'
    )
    time_cls = "result-time" if is_ranked else "result-time unranked"
    record = '<span class="result-record">New Record</span>' if result["is_new_record"] else ""
    best_cls = "result-best is-record" if result["is_new_record"] else "result-best"
    st.html(
        f'<section class="result-details tone-{tone}">'
        f'<h1 class="result-heading">{esc(result["heading"])}</h1>'
        f'<p class="result-banner {tone}">{esc(result["outcome_label"])}</p>'
        '<div class="result-clock">'
        '<p class="result-time-label">Time including penalties</p>'
        f'<p class="{time_cls}">{_time(result["adjusted_seconds"])}</p>{note}</div>'
        '<div class="result-breakdown">'
        '<dl class="result-stat-group">'
        + _row("Gameplay time", _time(result["raw_seconds"]), "timer")
        + penalty_rows
        + '</dl><dl class="result-stat-group">'
        + _row("Final Suspicion", f'{result["final_suspicion"]} / 100', "shield")
        + _row("Objectives Completed", f'{result["objectives_done"]} / {result["objectives_total"]}', "target")
        + "</dl></div>"
        f'<div class="{best_cls}">'
        '<span class="result-best-label">Personal best</span>'
        f'<strong class="result-best-time result-icon-trophy">{_time(result["personal_best_seconds"])}</strong>'
        f"{record}</div></section>"
    )


def _artwork(result: dict, tone: str) -> None:
    esc = html.escape
    description = esc(result["scene_caption"])
    image = result.get("scene_image")
    art = f'<img src="{esc(image)}" alt="{description}">' if image else f"<span>{description}</span>"
    st.html(
        f'<figure class="result-scene {tone}">'
        '<div class="result-art">'
        '<span class="result-corner result-c-tl" aria-hidden="true"></span>'
        '<span class="result-corner result-c-tr" aria-hidden="true"></span>'
        '<span class="result-corner result-c-bl" aria-hidden="true"></span>'
        '<span class="result-corner result-c-br" aria-hidden="true"></span>'
        f"{art}</div>"
        '<figcaption class="result-attribution">'
        f'<blockquote>“{esc(result["quote"])}”</blockquote>'
        f'<p>— {esc(result["quote_by"])}</p></figcaption></figure>'
    )


def render() -> None:
    header.render(context="Mission Debrief")
    with st.container(key="results"):
        try:
            result = get_mission_result()
        except Exception:
            st.error("Could not load your results. Please try again.")
            st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
            return

        tone = result["tone"] if result["tone"] in ("success", "partial", "failure") else ""
        render_audio_controller(track=track_for_result(result))
        stats, art = st.columns(2)
        with stats:
            _summary(result, tone)

        with art, st.container(key="result_visual"):
            _artwork(result, tone)
            with st.container(key="result_actions"):
                retry, menu = st.columns(2)
                with retry:
                    st.button("Try again", key="result_retry", on_click=go_to, args=(MISSION_BRIEFING,), width="stretch")
                with menu:
                    st.button("Main menu", key="result_menu", type="primary", on_click=go_to, args=(MAIN_MENU,), width="stretch")
