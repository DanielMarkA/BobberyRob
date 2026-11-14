import html

import streamlit as st

from ui.data_provider import RUN_CATEGORIES, get_leaderboard
from ui.formatting import format_time


def format_time(seconds: int) -> str:
    """Display only: 134 -> '02:14'. The backend owns the actual time values."""
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def render() -> None:
    with st.container(key="leaderboard_panel"):
        st.markdown(
            '<div class="lb-trophy">🏆</div>'
            '<div class="lb-title">GLOBAL LEADERBOARD</div>',
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
            '<span style="text-align:right">Time</span></div>'
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