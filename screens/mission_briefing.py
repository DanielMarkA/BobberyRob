import html

import streamlit as st

from ui.components import header
from ui.data_provider import get_mission_briefing, start_mission
from ui.navigation import go_to, reset_mission_state, GAMEPLAY, MAIN_MENU


def _item(icon: str, label: str, body_html: str, modifier: str = "", label_prefix: str = "") -> str:
    cls = f"brief-item {modifier}".strip()
    return (
        f'<section class="{cls}">'
        f'<span class="brief-icon brief-icon-{icon}" aria-hidden="true"></span>'
        f'<div class="brief-item-copy"><h2 class="brief-label">{label_prefix}{label}</h2>{body_html}</div>'
        "</section>"
    )


def _start_action() -> None:
    if not st.button("Start mission", type="primary", width="stretch", key="start_mission"):
        return
    try:
        result = start_mission()
    except Exception:
        st.error("Could not start the mission. Please try again.")
        return
    if not result["ok"]:
        st.error(result["error"])
        return

    reset_mission_state()
    go_to(GAMEPLAY)
    st.rerun()


def render() -> None:
    header.render(context="Mission Briefing")
    with st.container(key="mission_briefing"):
        try:
            mission = get_mission_briefing()
        except Exception:
            st.error("Could not load the mission briefing. Please try again.")
            st.button("Back to main menu", on_click=go_to, args=(MAIN_MENU,))
            return

        esc = html.escape
        location = esc(mission["location_name"])
        optional = "".join(f"<li>{esc(objective)}</li>" for objective in mission["optional_objectives"])
        art, text = st.columns(2)
        with art:
            image = mission["location_image"]
            if image:
                st.html(
                    '<figure class="brief-art">'
                    '<span class="brief-corner brief-c-tl" aria-hidden="true"></span>'
                    '<span class="brief-corner brief-c-tr" aria-hidden="true"></span>'
                    '<span class="brief-corner brief-c-bl" aria-hidden="true"></span>'
                    '<span class="brief-corner brief-c-br" aria-hidden="true"></span>'
                    f'<img src="{esc(image)}" alt="Mission target on display at {location}">'
                    '<figcaption class="brief-plate-caption">'
                    '<span class="brief-pin" aria-hidden="true"></span>'
                    f"<span>Target photo · {location}</span></figcaption>"
                    "</figure>"
                )
            else:
                st.html(
                    '<figure class="brief-art brief-art-empty">'
                    f"<figcaption>{location}</figcaption></figure>"
                )

        with text, st.container(key="brief_details"):
            alert_dot = '<span class="brief-alert-dot" aria-hidden="true"></span>'
            st.html(
                '<article class="brief-dossier" aria-label="Mission briefing">'
                '<div class="brief-intro">'
                f'<h1 class="brief-title">{esc(mission["title"])}</h1>'
                f'<p class="brief-summary">{esc(mission["summary"])}</p></div>'
                '<div class="brief-objectives">'
                + _item("primary", "Primary Objective", f'<p>{esc(mission["primary_objective"])}</p>', "brief-item-primary")
                + _item("optional", "Optional Objectives", f"<ul>{optional}</ul>")
                + _item("alert", "Security Alert", f'<p>{esc(mission["information"])}</p>', "brief-item-alert", alert_dot)
                + "</div></article>"
            )
            _start_action()
