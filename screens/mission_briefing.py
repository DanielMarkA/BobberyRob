import html

import streamlit as st

from ui.components import header
from ui.components.image_slot import image_slot
from ui.data_provider import get_mission_briefing, start_mission
from ui.navigation import go_to, GAMEPLAY, MAIN_MENU


def _item(number: str, label: str, body_html: str) -> str:
    return (
        '<div class="brief-item">'
        f'<div class="brief-num">{number}</div>'
        f'<div><div class="brief-label">{label}</div>'
        f'<div class="brief-text">{body_html}</div></div>'
        "</div>"
    )


def render() -> None:
    header.render()

    try:
        mission = get_mission_briefing()
    except Exception:
        st.error("Could not load the mission briefing. Please try again.")
        st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
        return

    esc = html.escape
    optional = "".join(f"<li>{esc(o)}</li>" for o in mission["optional_objectives"])

    col_img, col_text = st.columns([722, 766], gap="large")

    with col_img:
        image_slot("Mission location image", mission["location_name"])

    with col_text:
        st.markdown(
            '<div class="brief-eyebrow">Mission Briefing</div>'
            f'<div class="brief-title">{esc(mission["title"])}</div>'
            f'<div class="brief-summary">{esc(mission["summary"])}</div>'
            + _item("01", "Primary Objective", esc(mission["primary_objective"]))
            + _item("02", "Optional Objectives", f"<ul>{optional}</ul>")
            + _item("03", "Mission Information", esc(mission["information"])),
            unsafe_allow_html=True,
        )

    with st.container(key="start_action"):
        _, col_btn, _ = st.columns([1, 1.2, 1])
        with col_btn:
            if st.button("START MISSION  →", type="primary", width="stretch", key="start_mission"):
                try:
                    result = start_mission()
                except Exception:
                    st.error("Could not start the mission. Please try again.")
                    return
                if result["ok"]:
                    go_to(GAMEPLAY)
                    st.rerun()
                else:
                    st.error(result["error"])