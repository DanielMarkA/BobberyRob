import streamlit as st

from ui.components import leaderboard, game_entry

_SCREEN_CSS = """
.stApp {
  background:
    linear-gradient(rgba(5, 5, 5, 0.12), rgba(5, 5, 5, 0.3)),
    url("/app/static/backgrounds/museum_blur.webp") center / cover fixed no-repeat,
    var(--bg);
}
.block-container { max-width: 1280px; padding-top: clamp(1.5rem, 9vh, 6rem); }
.stApp [data-testid="stHorizontalBlock"] { gap: 24px; }
@media (max-width: 640px) {
  .stApp [data-testid="stHorizontalBlock"] { flex-direction: column-reverse; }
}
"""


def render() -> None:
    st.markdown(
        f'<style>{_SCREEN_CSS}</style><div class="screen-marker"></div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([554, 650], gap="small")

    with col_left:
        leaderboard.render()

    with col_right:
        game_entry.render()