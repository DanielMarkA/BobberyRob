import html

import streamlit as st


def render(items: list[dict]) -> None:
    rows = "".join(
        f'<li class="checkpoint-objective{" done" if item["done"] else ""}">'
        f'<span class="checkpoint-sr">{"Complete" if item["done"] else "Pending"}: </span>'
        f'{html.escape(item["text"])}</li>'
        for item in items
    )
    body = f'<ul>{rows}</ul>' if rows else '<p>No objectives yet.</p>'
    st.html(
        '<section class="checkpoint-card checkpoint-objectives">'
        '<h2 class="checkpoint-heading checkpoint-icon-objectives">Objectives</h2>'
        f'{body}</section>'
    )
