import html

import streamlit as st

from ui.data_provider import RUN_CATEGORIES, get_leaderboard
from ui.formatting import format_time


def render() -> None:
    with st.container(key="leaderboard_panel"):
        st.html(
            '<div class="lb-trophy" aria-hidden="true"></div>'
            '<h2 id="leaderboard-title" class="lb-title">Global Leaderboard</h2>'
        )

        category = st.segmented_control(
            "Run category",
            RUN_CATEGORIES,
            default=RUN_CATEGORIES[0],
            required=True,
            key="lb_category",
            label_visibility="collapsed",
            width="stretch",
        ) or RUN_CATEGORIES[0]

        try:
            entries = get_leaderboard(category)
        except Exception:
            st.html('<div class="lb-empty" role="status">Leaderboard unavailable right now.</div>')
            return

        table_start = (
            '<table class="lb-table" aria-labelledby="leaderboard-title">'
            '<colgroup><col class="lb-rank-col"><col><col class="lb-time-col"></colgroup>'
            '<thead><tr><th scope="col">#</th><th scope="col">Player</th>'
            '<th scope="col">Time</th></tr></thead><tbody>'
        )

        if not entries:
            body = '<tr><td class="lb-empty" colspan="3">No runs recorded yet.</td></tr>'
        else:
            rows = []
            for e in entries:
                top = ' class="top"' if e["rank"] == 1 else ""
                rows.append(
                    f'<tr{top}><td>{e["rank"]}.</td>'
                    f'<td class="lb-name">{html.escape(str(e["player"]))}</td>'
                    f'<td>{format_time(e["time_seconds"])}</td></tr>'
                )
            body = "".join(rows)

        st.html(table_start + body + "</tbody></table>")
