import html

import streamlit as st

from ui.data_provider import use_item


def _select(item_id: str) -> None:
    """Click an item to select it; click again to deselect."""
    current = st.session_state.get("selected_item")
    st.session_state["selected_item"] = None if current == item_id else item_id


def _queue_use() -> None:
    item_id = st.session_state.get("selected_item")
    if item_id:
        st.session_state["pending_item"] = item_id


def process_pending() -> None:
    """Call BEFORE drawing any panel, so every panel sees the updated state."""
    item_id = st.session_state.pop("pending_item", None)
    if item_id is None:
        return

    with st.spinner("Using item..."):
        try:
            st.session_state["game"] = use_item(item_id)
            st.session_state.pop("item_error", None)
        except Exception:
            st.session_state["item_error"] = "Could not use that item. Please try again."


def render(items: list[dict]) -> None:
    # Drop the selection if that item vanished or ran out.
    usable_ids = {i["id"] for i in items if i["quantity"] > 0}
    selected = st.session_state.get("selected_item")
    if selected not in usable_ids:
        selected = st.session_state["selected_item"] = None

    with st.container(key="card_inventory"):
        st.markdown('<div class="card-title">Inventory</div>', unsafe_allow_html=True)

        if not items:
            st.markdown('<div class="card-text">Your inventory is empty.</div>',
                        unsafe_allow_html=True)
            return

        for item in items:
            # The key changes when selected, so CSS can style the selected row.
            row_key = f"item_sel_{item['id']}" if item["id"] == selected else f"item_{item['id']}"
            with st.container(key=row_key):
                col_icon, col_btn = st.columns([1, 4], gap="small", vertical_alignment="center")
                with col_icon:
                    st.markdown(
                        f'<div class="item-icon">{html.escape(str(item["icon"]))}</div>',
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    st.button(
                        f'{item["name"]}   ×{item["quantity"]}',
                        key=f"pick_{item['id']}",
                        on_click=_select,
                        args=(item["id"],),
                        disabled=item["quantity"] <= 0,
                        width="stretch",
                    )

        st.button(
            "Use item",
            key="use_item",
            type="primary",
            on_click=_queue_use,
            disabled=selected is None,
            width="stretch",
        )

        if "item_error" in st.session_state:
            st.error(st.session_state["item_error"])