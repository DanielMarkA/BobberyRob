import html

import streamlit as st

from ui.data_provider import RUN_CATEGORIES, get_leaderboard
from ui.formatting import format_time
from ui.icons import icon


def render() -> None:
    with st.container(key="leaderboard_panel"):
        st.markdown(
            f'<div class="lb-trophy">{icon("trophy", 64)}</div>'
            '<div class="lb-title">Global Leaderboard</div>',
            unsafe_allow_html=True,
        )

        # segmented_control returns None if the user un-selects, so fall back.
        category = st.segmented_control(
            "Run category",
            RUN_CATEGORIES,
            default=RUN_CATEGORIES[0],
            key="lb_category",
            label_visibility="collapsed",
        ) or RUN_CATEGORIES[0]

        try:
            entries = get_leaderboard(category)
        except Exception:
            st.markdown('<div class="lb-empty">Leaderboard unavailable right now.</div>',
                        unsafe_allow_html=True)
            return

        header = (
            '<div class="lb-head"><span>#</span><span>Player</span>'
            f'<span class="lb-time-h">{icon("timer", 18)}Time</span></div>'
        )

        if not entries:
            body = '<div class="lb-empty">No runs recorded yet.</div>'
        else:
            rows = []
            for e in entries:
                top = " top" if e["rank"] == 1 else ""
                rows.append(
                    f'<div class="lb-row{top}">'
                    f'<span>{e["rank"]}.</span>'
                    f'<span class="lb-name">{html.escape(str(e["player"]))}</span>'
                    f'<span class="lb-time">{format_time(e["time_seconds"])}</span>'
                    f'</div>'
                )
            body = "".join(rows)

        st.markdown(header + body, unsafe_allow_html=True)