"""Location graph validation, route unlocking, and objective progression."""

from typing import Optional

from game.state import GameState, MoveResult
from scenario.loader import GuardDef, ObjectiveDef, RouteDef, ScenarioConfig


class RouteManager:
    """Enforces scenario routes, movement locks, and objective completion."""

    def __init__(self, scenario: ScenarioConfig) -> None:
        self._scenario = scenario
        self._guards_by_location: dict[str, GuardDef] = {
            guard.assigned_location: guard for guard in scenario.guards.values()
        }
        self._objectives_by_target: dict[str, ObjectiveDef] = {
            obj.target: obj
            for obj in scenario.objectives.values()
            if obj.completion_type == "location_reached"
        }

    def guard_for_location(self, location_id: str) -> GuardDef:
        if location_id not in self._guards_by_location:
            raise KeyError(f"No guard assigned to location '{location_id}'")
        return self._guards_by_location[location_id]

    def objective_for_location(self, location_id: str) -> Optional[ObjectiveDef]:
        return self._objectives_by_target.get(location_id)

    def find_route(self, from_location: str, to_location: str) -> Optional[RouteDef]:
        for route in self._scenario.routes:
            if route.from_location == from_location and route.to_location == to_location:
                return route
        return None

    def complete_objective(self, state: GameState, objective_id: str) -> bool:
        """Mark a known scenario objective as completed. Returns True if newly completed."""
        if objective_id not in self._scenario.objectives:
            return False
        if objective_id in state.completed_objectives:
            return False
        state.completed_objectives.append(objective_id)
        return True

    def can_move(
        self,
        state: GameState,
        target_location: str,
    ) -> tuple[bool, bool, Optional[str]]:
        """Validate whether moving to `target_location` is permitted.

        Returns `(valid_route, transition_allowed, reason_if_blocked)`.
        """
        from_loc = state.current_location
        if target_location not in self._scenario.locations:
            return False, False, f"Unknown location '{target_location}'."

        if target_location == from_loc:
            return False, False, "You are already at this location."

        route = self.find_route(from_loc, target_location)
        if route is None:
            from_name = self._scenario.locations[from_loc].name
            to_name = self._scenario.locations[target_location].name
            return (
                False,
                False,
                f"You cannot reach {to_name} directly from {from_name}.",
            )

        if state.ended:
            return True, False, "The mission has already ended."

        if state.interrogation.active:
            return True, False, "Movement is locked during interrogation."

        is_forward = route.condition is not None
        if is_forward and state.suspicion >= 80:
            return (
                True,
                False,
                "Security alert is too high. De-escalate suspicion before advancing.",
            )

        if route.condition is not None:
            cond = route.condition
            if cond.type == "objective_completed" and cond.objective_id:
                if cond.objective_id not in state.completed_objectives:
                    obj = self._scenario.objectives[cond.objective_id]
                    return (
                        True,
                        False,
                        f"Complete '{obj.name}' before proceeding.",
                    )
            elif cond.type == "item_required" and cond.item_id:
                if state.inventory.get(cond.item_id, 0) <= 0:
                    item = self._scenario.items[cond.item_id]
                    return True, False, f"You need {item.name} to proceed."

        return True, True, None

    def available_routes(self, state: GameState) -> list[dict]:
        """List adjacent routes from the current location with unlock status."""
        results: list[dict] = []
        for route in self._scenario.routes:
            if route.from_location != state.current_location:
                continue
            _, allowed, reason = self.can_move(state, route.to_location)
            loc_def = self._scenario.locations[route.to_location]
            results.append(
                {
                    "to_location": route.to_location,
                    "name": loc_def.name,
                    "unlocked": allowed,
                    "reason": reason,
                    "is_forward": route.condition is not None,
                }
            )
        return results

    def move_to(self, state: GameState, target_location: str) -> MoveResult:
        """Validate and perform a location transition."""
        from_loc = state.current_location
        valid_route, allowed, reason = self.can_move(state, target_location)

        if not allowed:
            state.last_notice = reason
            return MoveResult(
                valid_route=valid_route,
                transition_allowed=False,
                from_location=from_loc,
                target_location=target_location,
                current_location_after=from_loc,
                notice=reason,
            )

        state.current_location = target_location
        if target_location not in state.visited_locations:
            state.visited_locations.append(target_location)

        guard = self.guard_for_location(target_location)
        loc_def = self._scenario.locations[target_location]
        state.active_speaker = guard.name
        state.active_dialogue = guard.opening_line
        state.consecutive_evasions = 0
        state.last_notice = f"Entered {loc_def.name}."

        return MoveResult(
            valid_route=True,
            transition_allowed=True,
            from_location=from_loc,
            target_location=target_location,
            current_location_after=target_location,
            notice=state.last_notice,
            guard_opening_line=guard.opening_line,
        )

    def serialize_objectives(self, state: GameState) -> list[dict]:
        """Return objective checklist matching the Streamlit UI contract."""
        return [
            {
                "id": obj.id,
                "text": obj.text,
                "done": obj.id in state.completed_objectives,
            }
            for obj in self._scenario.objectives.values()
        ]
