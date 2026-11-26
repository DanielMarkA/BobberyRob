"""Sync the current checkpoint's browser interactions across Streamlit reruns."""

import json
from pathlib import Path

import streamlit as st

_SCRIPT = Path(__file__).with_suffix(".js").read_text(encoding="utf-8")


def render(scene: str, items: dict | None = None) -> None:
    payload = json.dumps([scene, items or {}]).replace("<", "\\u003c")
    st.html(
        f"<script>({_SCRIPT.strip()})({payload});</script>",
        unsafe_allow_javascript=True,
    )
