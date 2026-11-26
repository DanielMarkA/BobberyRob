import html

import streamlit as st


def render(items: list[dict]) -> None:
    done_count = sum(1 for item in items if item.get("done"))
    total_count = len(items)
    counter = (
        f'<span class="checkpoint-count" aria-hidden="true">{done_count}/{total_count}</span>'
        if total_count
        else ""
    )

    next_assigned = False
    row_parts = []
    for item in items:
        if item["done"]:
            modifier = " done"
            sr = "Complete"
        elif not next_assigned:
            modifier = " next"
            sr = "Current"
            next_assigned = True
        else:
            modifier = ""
            sr = "Pending"
        row_parts.append(
            f'<li class="checkpoint-objective{modifier}">'
            f'<span class="checkpoint-sr">{sr}: </span>'
            f"<span>{html.escape(item['text'])}</span></li>"
        )
    rows = "".join(row_parts)
    body = f"<ul>{rows}</ul>" if rows else "<p>No objectives yet.</p>"
    st.html(
        '<section class="checkpoint-card checkpoint-objectives">'
        '<div class="checkpoint-card-head">'
        '<h2 class="checkpoint-heading checkpoint-icon-objectives">Objectives</h2>'
        f"{counter}</div>"
        f"{body}</section>"
    )
