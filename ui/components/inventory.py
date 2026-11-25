import streamlit as st

from ui.audio import queue_sfx
from ui.data_provider import use_item


def _select(item_id: str) -> None:
    """Click an item to select it; click again to deselect."""
    current = st.session_state.get("selected_item")
    st.session_state["selected_item"] = None if current == item_id else item_id


def _queue_use() -> None:
    item_id = st.session_state.get("selected_item")
    if item_id:
        st.session_state["pending_item"] = item_id


def process_pending() -> bool:
    """Execute a queued item presentation after stable UI has rendered."""
    item_id = st.session_state.pop("pending_item", None)
    if item_id is None:
        return False

    prev_susp = int(((st.session_state.get("game") or {}).get("suspicion") or {}).get("value", 0))
    try:
        new_game = use_item(item_id)
        st.session_state["game"] = new_game
        st.session_state.pop("item_error", None)
        new_susp = int((new_game.get("suspicion") or {}).get("value", 0))
        notice_low = str(new_game.get("notice") or "").lower()
        if new_susp > prev_susp or "don't have" in notice_low or "cannot be used" in notice_low:
            queue_sfx("item_fail")
        else:
            queue_sfx("item_success")
    except Exception:
        st.session_state["item_error"] = "Could not use that item. Please try again."
    return True


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

        selected_item = None
        for item in items:
            is_selected = item["id"] == selected
            if is_selected:
                selected_item = item
            image = f'![]({item["image"]}) ' if item.get("image") else ""
            st.button(
                f'{image}{item["name"]} `×{item["quantity"]}`',
                key=f"pick_{item['id']}",
                type="primary" if is_selected else "secondary",
                on_click=_select,
                args=(item["id"],),
                disabled=item["quantity"] <= 0,
                width="stretch",
            )

        if selected_item is not None:
            st.button(
                f'Present {selected_item["name"]}',
                key="use_item",
                type="primary",
                on_click=_queue_use,
                width="stretch",
            )
        else:
            st.html('<p class="inv-hint">Hover to inspect · click to select.</p>')
