import streamlit as st
from ui.navigation import go_to, MISSION_BRIEFING


def render() -> None:
    st.title("Bobbery Rob")
    st.caption("Screen: Starting (placeholder)")
    st.button("Enter Game", on_click=go_to, args=(MISSION_BRIEFING,))