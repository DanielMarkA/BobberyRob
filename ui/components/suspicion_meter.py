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

    st.html(
        '<section class="checkpoint-card checkpoint-suspicion">'
        '<h2 id="checkpoint-suspicion-title" class="checkpoint-heading checkpoint-icon-suspicion">'
        'Suspicion Level</h2>'
        f'<div class="susp-value" aria-hidden="true">{value:.0f} / 100</div>'
        f'<div class="susp-track" role="meter" aria-labelledby="checkpoint-suspicion-title" '
        f'aria-valuenow="{value:g}" aria-valuemin="0" aria-valuemax="100">'
        f'<div class="susp-fill {_level(value)}" style="width:{value}%"></div></div>'
        f'<p class="susp-label">{html.escape(str(suspicion["label"]))}</p>'
        '</section>'
    )
