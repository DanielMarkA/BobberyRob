import html

import streamlit as st


def image_slot(label: str, caption: str = "", ratio: str = "722 / 585") -> None:
    """Placeholder for artwork. `ratio` is a CSS aspect-ratio (width / height)."""
    st.markdown(
        f'<div class="img-slot" style="aspect-ratio:{ratio}">'
        f'<div class="img-slot-label">{html.escape(label)}</div>'
        f'<div class="img-slot-caption">{html.escape(caption)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )