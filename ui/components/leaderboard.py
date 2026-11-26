import html
import logging

import streamlit as st

from ui.data_provider import RUN_CATEGORIES, get_leaderboard
from ui.formatting import format_time

log = logging.getLogger(__name__)


def render() -> None:
    with st.container(key="leaderboard_panel"):
        st.html(
            '<div class="lb-head">'
            '<span class="lb-trophy" aria-hidden="true"></span>'
            '<h2 id="leaderboard-title" class="lb-title">Global Leaderboard</h2>'
            "</div>"
        )

        category = (
            st.segmented_control(
                "Run category",
                RUN_CATEGORIES,
                default=RUN_CATEGORIES[0],
                required=True,
                key="lb_category",
                label_visibility="collapsed",
                width="stretch",
            )
            or RUN_CATEGORIES[0]
        )

        try:
            entries = get_leaderboard(category)
        except Exception:
            log.exception("Leaderboard query failed")
            st.html('<div class="lb-empty" role="status">Leaderboard unavailable right now.</div>')
            return

        if not entries:
            st.html(
                '<div class="lb-table-wrap">'
                '<table class="lb-table" aria-labelledby="leaderboard-title">'
                '<colgroup><col class="lb-rank-col"><col><col class="lb-time-col"></colgroup>'
                '<thead><tr><th scope="col">Rank</th><th scope="col">Codename</th>'
                '<th scope="col">Time</th></tr></thead>'
                '<tbody><tr><td class="lb-empty" colspan="3">No runs recorded in this category yet.</td></tr></tbody>'
                "</table></div>"
            )
            return

        leader = entries[0]
        podium_html = (
            '<div class="lb-podium" aria-label="Top ranked run">'
            '<div class="lb-podium-left">'
            f'<span class="lb-podium-rank">{leader["rank"]:02d}</span>'
            f'<span class="lb-podium-name">{html.escape(str(leader["player"]))}</span>'
            "</div>"
            f'<span class="lb-podium-time">{format_time(leader["time_seconds"])}</span>'
            "</div>"
        )

        rows = "".join(
            f'<tr><td class="lb-rank">{e["rank"]:02d}</td>'
            f'<td class="lb-name">{html.escape(str(e["player"]))}</td>'
            f'<td class="lb-time">{format_time(e["time_seconds"])}</td></tr>'
            for e in entries[1:]
        )

        table_html = (
            '<div class="lb-table-wrap">'
            '<table class="lb-table" aria-labelledby="leaderboard-title">'
            '<colgroup><col class="lb-rank-col"><col><col class="lb-time-col"></colgroup>'
            '<thead><tr><th scope="col">Rank</th><th scope="col">Codename</th>'
            '<th scope="col">Time</th></tr></thead>'
            f"<tbody>{rows}</tbody></table></div>"
            if rows
            else ""
        )

        st.html(podium_html + table_html)
