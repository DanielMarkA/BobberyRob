import streamlit as st
from ui.navigation import go_to, GAMEPLAY


def render() -> None:
    st.title("Mission Briefing")
    st.caption("Screen: Mission Briefing (placeholder)")
    st.button("Start Mission", on_click=go_to, args=(GAMEPLAY,))