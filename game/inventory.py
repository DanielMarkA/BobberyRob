"""Backend-validated inventory ownership, usage conditions, and effects."""

from game.state import GameState, ItemUseResult
from scenario.loader import GuardDef, ItemDef, ScenarioConfig


class InventoryManager:
    """Validates and executes all inventory item actions using scenario rules."""

    def __init__(self, scenario: ScenarioConfig) -> None:
        self._scenario = scenario

    def initial_quantities(self) -> dict[str, int]:
        """Build the initial item_id -> quantity mapping from scenario config."""
        quantities = {
            item_id: item_def.starting_quantity
            for item_id, item_def in self._scenario.items.items()
        }
        for entry in self._scenario.starting_inventory:
            item_id = entry.get("id")
            if item_id in quantities and "quantity" in entry:
                quantities[item_id] = int(entry["quantity"])
        return quantities

    def item_document_details(self, state: GameState, item_id: str) -> dict[str, str]:
        """Return the fictional printed details visible when inspecting an inventory item.

        Uses the player's Main Menu codename on the Fake Passport without ever
        exposing the hidden conversation identity record.
        """
        holder = (state.codename or "Unlisted Bearer").strip()
        qty = state.inventory.get(item_id, 0)

        if item_id == "fake_passport":
            return {
                "header": "INTERNATIONAL PASSPORT (FORGED)",
                "lines": (
                    f"Holder: {holder}\n"
                    "Passport No.: INT-4829-AR\n"
                    "Visa Stamp: Visiting Academic Research Visa\n"
                    "Note: Forged watermark — passes casual checks, but observant officers can spot it."
                ),
                "tooltip": (
                    f"**INTERNATIONAL PASSPORT (FORGED)**\n\n"
                    f"- **Holder:** {holder}\n"
                    f"- **Passport No.:** `INT-4829-AR`\n"
                    f"- **Visa:** Visiting Academic Research Visa\n"
                    f"- **Warning:** Forged watermark — risky at Security Checkpoint."
                ),
            }
        if item_id == "invitation_letter":
            return {
                "header": "VIP GALA INVITATION",
                "lines": (
                    "Event: Grand Museum Annual Benefactors Gala\n"
                    "Venue: East Pavilion Hall (Public Gala Wing)\n"
                    "Signed By: Eleanor Vance, Museum Board President\n"
                    "Valid: Tonight, 7:00 PM – 11:00 PM"
                ),
                "tooltip": (
                    "**VIP GALA INVITATION**\n\n"
                    "- **Event:** Grand Museum Annual Benefactors Gala\n"
                    "- **Venue:** East Pavilion Hall (Public Gala Wing)\n"
                    "- **Signed By:** Eleanor Vance, Museum Board President\n"
                    "- **Hours:** Tonight, 7:00 PM – 11:00 PM"
                ),
            }
        if item_id == "bribe_money":
            return {
                "header": f"UNMARKED CASH ENVELOPE (×{qty})",
                "lines": (
                    "Contents: Crisp unmarked bills\n"
                    "Use: Calms casual or hurried guards (-15 suspicion).\n"
                    "Warning: Strict, observant, or veteran officers will detain you for bribery."
                ),
                "tooltip": (
                    f"**UNMARKED CASH ENVELOPE (×{qty})**\n\n"
                    "- **Effect:** Lowers suspicion with casual or impatient guards.\n"
                    "- **Warning:** Offering cash to strict, observant, or veteran officers triggers Interrogation."
                ),
            }
        if item_id == "access_card":
            return {
                "header": "LEVEL-4 CURATOR ACCESS CARD",
                "lines": (
                    "Clearance: Level-4 Senior Curator\n"
                    "Card ID: GM-CUR-0419\n"
                    "Zones: Restricted Collection Area & Vault Sanctum\n"
                    "Note: Single-use magnetic pass."
                ),
                "tooltip": (
                    "**LEVEL-4 CURATOR ACCESS CARD**\n\n"
                    "- **Clearance:** Level-4 Senior Curator (`GM-CUR-0419`)\n"
                    "- **Zones:** Restricted Collection Area & Vault Sanctum\n"
                    "- **Note:** Single-use pass; supports cover story & lowers suspicion."
                ),
            }

        item_def = self._scenario.items.get(item_id)
        desc = item_def.description if item_def else ""
        return {
            "header": (item_def.name if item_def else item_id).upper(),
            "lines": desc,
            "tooltip": desc,
        }

    def serialize_for_ui(self, state: GameState, include_empty: bool = False) -> list[dict]:
        """Return inventory list matching the Streamlit UI contract.

        Items whose quantity reaches 0 are removed from the player's inventory
        unless `include_empty=True`.
        """
        items_out: list[dict] = []
        for entry in self._scenario.starting_inventory:
            item_id = entry["id"]
            qty = state.inventory.get(item_id, 0)
            if not include_empty and qty <= 0:
                continue
            item_def = self._scenario.items.get(item_id)
            details = self.item_document_details(state, item_id)
            items_out.append(
                {
                    "id": item_id,
                    "name": item_def.name if item_def else entry["name"],
                    "quantity": qty,
                    "image": (item_def.image if item_def else "") or entry.get("image", ""),
                    "description": item_def.description if item_def else "",
                    "inspect_header": details["header"],
                    "inspect_lines": details["lines"],
                    "tooltip": details["tooltip"],
                }
            )
        return items_out

    def serialize_for_llm(self, state: GameState) -> list[dict]:
        """Return currently held items (quantity > 0) with printed details for LLM grounding."""
        return [
            {
                "id": item_id,
                "name": self._scenario.items[item_id].name,
                "quantity": qty,
                "printed_details": self.item_document_details(state, item_id)["lines"],
            }
            for item_id, qty in state.inventory.items()
            if qty > 0 and item_id in self._scenario.items
        ]

    def grant_item(self, state: GameState, item_id: str, amount: int = 1) -> int:
        """Grant quantity of a known scenario item. Returns new quantity."""
        if item_id not in self._scenario.items:
            raise KeyError(f"Unknown scenario item '{item_id}'")
        state.inventory[item_id] = max(0, state.inventory.get(item_id, 0) + int(amount))
        return state.inventory[item_id]

    def use_item(
        self,
        state: GameState,
        item_id: str,
        guard: GuardDef,
        location_id: str | None = None,
    ) -> ItemUseResult:
        """Validate ownership, conditions, and apply configured item effects.

        Note: This mutates `state.inventory`, `state.items_used`, and
        `state.items_presented_log` when valid, but returns `suspicion_delta`
        for the engine to apply through SuspicionManager.
        """
        loc_id = location_id or state.current_location
        item_def: ItemDef | None = self._scenario.items.get(item_id)

        if item_def is None:
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=0,
                suspicion_delta=0,
                dialogue=state.active_dialogue,
                notice="You don't have that item.",
            )

        current_qty = state.inventory.get(item_id, 0)
        min_qty = int(item_def.usage_conditions.get("min_quantity", 1))
        if current_qty < max(1, min_qty):
            if "min_quantity" in item_def.usage_conditions:
                notice = f"You don't have enough {item_def.name.lower()}."
            else:
                notice = "You don't have that item."
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=current_qty,
                suspicion_delta=0,
                dialogue=state.active_dialogue,
                notice=notice,
            )

        # Check location restriction if configured
        allowed_locations = item_def.usage_conditions.get("locations")
        if allowed_locations and loc_id not in allowed_locations:
            loc_name = self._scenario.locations[loc_id].name
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=current_qty,
                suspicion_delta=0,
                dialogue=state.active_dialogue,
                notice=f"{item_def.name} cannot be used at {loc_name}.",
            )

        # Look up guard-specific configured effect
        effect = item_def.effects.get(guard.id)
        if effect is None:
            failed_delta = int(
                self._scenario.suspicion_settings.event_table["failed_item_use"]["delta"]
            )
            state.items_presented_log.append(
                {
                    "item_id": item_id,
                    "guard_id": guard.id,
                    "location_id": loc_id,
                    "outcome": "failure",
                }
            )
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="failure",
                consumed=item_id == "bribe_money",
                quantity_after=max(0, current_qty - 1) if item_id == "bribe_money" else current_qty,
                suspicion_delta=failed_delta,
                dialogue="Put that away. That won't work on me.",
                notice=f"{guard.name} rejected your {item_def.name.lower()}.",
                triggers_interrogation=(item_id == "bribe_money"),
            )

        consumed = bool(effect.consumed)
        if consumed:
            state.inventory[item_id] = max(0, current_qty - 1)
        qty_after = state.inventory.get(item_id, 0)

        if item_id not in state.items_used:
            state.items_used.append(item_id)
        state.items_presented_log.append(
            {
                "item_id": item_id,
                "guard_id": guard.id,
                "location_id": loc_id,
                "outcome": effect.outcome,
            }
        )

        is_success = effect.outcome in ("success", "partial_success")
        return ItemUseResult(
            item_id=item_id,
            success=is_success,
            outcome=effect.outcome,
            consumed=consumed,
            quantity_after=qty_after,
            suspicion_delta=int(effect.suspicion_delta),
            dialogue=effect.dialogue,
            notice=effect.notice,
            triggers_interrogation=bool(effect.triggers_interrogation),
        )
