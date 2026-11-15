import streamlit as st

from ui.components import leaderboard, game_entry

_BACKGROUND_CSS = """
.stApp {
  background:
    linear-gradient(rgba(5, 5, 5, 0.35), rgba(5, 5, 5, 0.55)),
    url("/app/static/backgrounds/museum_blur.webp") center / cover fixed no-repeat,
    var(--bg);
}
"""


def render() -> None:
    st.markdown(
        f'<style>{_BACKGROUND_CSS}</style><div class="screen-marker"></div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([554, 650], gap="large")

    with col_left:
        leaderboard.render()

    with col_right:
        game_entry.render()