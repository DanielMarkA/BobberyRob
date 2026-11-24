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

    with st.container(key="checkpoint_inventory"):
        st.html(
            '<div class="checkpoint-card-head">'
            '<h2 class="checkpoint-heading checkpoint-icon-inventory">Inventory</h2>'
            "</div>"
        )

        if not items:
            st.html('<p class="inv-hint">Your inventory is empty.</p>')
            return

        selected_name = None
        for item in items:
            if item["id"] == selected:
                selected_name = item["name"]
            image = f'![]({item["image"]}) ' if item.get("image") else ""
            st.button(
                f'{image}{item["name"]} `×{item["quantity"]}`',
                key=f"pick_{item['id']}",
                type="primary" if item["id"] == selected else "secondary",
                on_click=_select,
                args=(item["id"],),
                disabled=item["quantity"] <= 0,
                width="stretch",
            )

        if selected is not None and selected_name:
            st.button(
                f"Present {selected_name}",
                key="use_item",
                type="primary",
                on_click=_queue_use,
                width="stretch",
            )
        else:
            st.html('<p class="inv-hint">Select an item to present it.</p>')
