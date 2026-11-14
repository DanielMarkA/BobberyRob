import streamlit as st
from ui.navigation import go_to, MAIN_MENU, MISSION_BRIEFING


def render() -> None:
    st.title("Mission Results")
    st.caption("Screen: Results (placeholder)")

    col_retry, col_menu = st.columns(2)
    with col_retry:
        st.button("Retry", on_click=go_to, args=(MISSION_BRIEFING,), use_container_width=True)
    with col_menu:
        st.button("Main Menu", on_click=go_to, args=(MAIN_MENU,), use_container_width=True)