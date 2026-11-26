import html

import streamlit as st

_VU_SEGMENTS = 20


def _level(value: float) -> str:
    """Visual tier only (matches the doc's bands). The backend owns the actual value."""
    if value >= 80:
        return "high"
    if value >= 40:
        return "mid"
    return "low"


def _segment_zone(index: int) -> str:
    if index >= 16:
        return "high"
    if index >= 8:
        return "mid"
    return "low"


def render(suspicion: dict) -> None:
    value = max(0, min(100, float(suspicion["value"])))  # clamp for display safety
    level = _level(value)
    lit_count = round(value / (100 / _VU_SEGMENTS))

    segments = "".join(
        f'<span class="susp-seg zone-{_segment_zone(i)}{" lit" if i <= lit_count else ""}"></span>'
        for i in range(1, _VU_SEGMENTS + 1)
    )

    st.html(
        f'<section class="checkpoint-card checkpoint-suspicion tier-{level}">'
        '<div class="checkpoint-card-head">'
        '<h2 id="checkpoint-suspicion-title" class="checkpoint-heading checkpoint-icon-suspicion">'
        "Suspicion</h2>"
        f'<span class="susp-value" aria-hidden="true">{value:.0f}<span class="susp-denom">/100</span></span>'
        "</div>"
        '<div class="susp-meter-wrap">'
        f'<div class="susp-meter" role="meter" aria-labelledby="checkpoint-suspicion-title" '
        f'aria-valuenow="{value:g}" aria-valuemin="0" aria-valuemax="100">'
        f"{segments}</div>"
        '<div class="susp-scale" aria-hidden="true">'
        '<span class="susp-tick" style="left:0%">0</span>'
        '<span class="susp-tick" style="left:40%">40</span>'
        '<span class="susp-tick" style="left:80%">80</span>'
        '<span class="susp-tick susp-tick-end" style="left:100%">100</span>'
        "</div></div>"
        '<p class="susp-label">'
        '<span class="susp-dot" aria-hidden="true"></span>'
        f"<span>{html.escape(str(suspicion['label']))}</span></p>"
        "</section>"
    )
