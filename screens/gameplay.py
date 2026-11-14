import streamlit as st
from ui.navigation import go_to, RESULTS


def render() -> None:
    st.title("Gameplay")
    st.caption("Screen: Gameplay (placeholder)")
    st.button("End Mission (temporary)", on_click=go_to, args=(RESULTS,))