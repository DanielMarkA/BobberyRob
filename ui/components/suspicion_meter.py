import html

import streamlit as st


def _level(value: float) -> str:
    """Visual tier only (matches the doc's bands). The backend owns the actual value."""
    if value >= 80:
        return "high"
    if value >= 40:
        return "mid"
    return "low"


def render(suspicion: dict) -> None:
    value = max(0, min(100, float(suspicion["value"])))  # clamp for display safety

    with st.container(key="card_suspicion"):
        st.markdown(
            '<div class="card-title">Suspicion Level</div>'
            f'<div class="susp-value">{value:.0f}<span> / 100</span></div>'
            f'<div class="susp-track"><div class="susp-fill {_level(value)}" '
            f'style="width:{value}%"></div></div>'
            f'<div class="susp-label">{html.escape(str(suspicion["label"]))}</div>',
            unsafe_allow_html=True,
        )