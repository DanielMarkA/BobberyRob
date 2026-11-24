import streamlit as st

from ui.data_provider import get_mission_elapsed_seconds


@st.fragment(run_every=1)
def render() -> None:
    elapsed = get_mission_elapsed_seconds()
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    st.html(
        '<section class="checkpoint-card checkpoint-timer">'
        '<h2 class="checkpoint-heading checkpoint-icon-time">Game time</h2>'
        f'<time role="timer" aria-label="Elapsed game time" datetime="PT{elapsed}S">'
        f'{hours:02d}:{minutes:02d}:{seconds:02d}</time>'
        '</section>'
    )
