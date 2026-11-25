"""Ending selection, challenge tracking, and debrief payload formatting."""

from typing import Any, Optional

from game.state import GameState
from scenario.loader import EndingDef, ScenarioConfig

ENDING_TO_CATEGORY: dict[str, Optional[str]] = {
    "perfect_infiltration": "Perfect Run",
    "successful_infiltration": "Successful Run",
    "compromised_victory": "Compromised Run",
    "alternate_ending": "Alternative Run",
    "capture_failure": None,
}

# Polished debrief artwork overrides (falling back to scenario ending scene_image)
DEBRIEF_IMAGE_MAP: dict[str, str] = {
    "perfect_infiltration": "/app/static/images/debrief_success.webp",
    "successful_infiltration": "/app/static/images/debrief_success.webp",
    "compromised_victory": "/app/static/images/debrief_compromised.webp",
    "capture_failure": "/app/static/images/debrief_captured.webp",
}


class EndingEvaluator:
    """Deterministically selects mission endings and formats debrief results."""

    def __init__(self, scenario: ScenarioConfig) -> None:
        self._scenario = scenario

    def can_voluntary_exit(self, state: GameState) -> bool:
        """Check whether the player qualifies for the voluntary Alternate Ending."""
        alt = self._scenario.endings.get("alternate_ending")
        if alt is None or state.ended or state.interrogation.active:
            return False

        conds = alt.conditions
        required_item = conds.get("item_used")
        if required_item and required_item not in state.items_used:
            return False

        required_loc = conds.get("location_reached")
        if required_loc and required_loc not in state.visited_locations:
            return False

        suspicion_below = conds.get("suspicion_below")
        if suspicion_below is not None and state.suspicion >= int(suspicion_below):
            return False

        return True

    def evaluate(self, state: GameState) -> Optional[EndingDef]:
        """Evaluate current game state and return a matching EndingDef, or None."""
        # 1. Capture / Failure
        if state.interrogation_failed:
            return self._scenario.endings.get("capture_failure")

        # 2. Alternate Ending (voluntary scholarly exit)
        if state.voluntary_exit and self.can_voluntary_exit(state):
            return self._scenario.endings.get("alternate_ending")

        # 3. Mission completion endings (requires primary retrieve_artifact objective)
        if "retrieve_artifact" not in state.completed_objectives:
            return None

        unresolved_count = len(state.unresolved_contradictions)

        # Perfect Infiltration
        perfect = self._scenario.endings.get("perfect_infiltration")
        if perfect and self._matches_victory_conditions(state, perfect, unresolved_count):
            return perfect

        # Successful Infiltration
        successful = self._scenario.endings.get("successful_infiltration")
        if successful and self._matches_victory_conditions(
            state, successful, unresolved_count
        ):
            return successful

        # Compromised Victory (catch-all when artifact is retrieved under high heat)
        return self._scenario.endings.get("compromised_victory") or successful

    def evaluate_challenges(self, state: GameState) -> dict[str, bool]:
        """Evaluate optional and hidden scenario challenges."""
        results: dict[str, bool] = {}
        for key, info in self._scenario.challenges.items():
            cond = info.get("condition")
            if cond == "zero_interrogations":
                results[key] = state.interrogations_triggered == 0
            elif cond == "zero_unresolved_contradictions":
                results[key] = len(state.unresolved_contradictions) == 0
        return results

    def category_for(self, ending_id: str) -> Optional[str]:
        return ENDING_TO_CATEGORY.get(ending_id)

    def build_result_payload(
        self,
        state: GameState,
        ending: EndingDef,
        raw_seconds: float,
        personal_best_seconds: Optional[float] = None,
        is_new_record: bool = False,
    ) -> dict[str, Any]:
        """Build the results screen dictionary matching `screens/results.py`."""
        penalties = [p.to_dict() for p in state.penalties]
        total_penalty = sum(p["seconds"] for p in penalties)

        is_failure = ending.tone == "failure"
        adjusted_seconds: Optional[float] = (
            None if is_failure else round(float(raw_seconds) + total_penalty, 2)
        )

        scene_image = DEBRIEF_IMAGE_MAP.get(ending.id) or ending.scene_image

        return {
            "ending_id": ending.id,
            "title": ending.title,
            "category": self.category_for(ending.id),
            "heading": ending.heading,
            "outcome_label": ending.outcome_label,
            "tone": ending.tone,
            "raw_seconds": round(float(raw_seconds), 2),
            "penalties": penalties,
            "adjusted_seconds": adjusted_seconds,
            "final_suspicion": state.suspicion,
            "objectives_done": len(state.completed_objectives),
            "objectives_total": len(self._scenario.objectives),
            "personal_best_seconds": personal_best_seconds,
            "is_new_record": is_new_record,
            "quote": ending.quote,
            "quote_by": ending.quote_by,
            "narration_seed": ending.narration_seed,
            "scene_image": scene_image,
            "scene_caption": ending.scene_caption,
            "challenges": self.evaluate_challenges(state),
        }

    def _matches_victory_conditions(
        self,
        state: GameState,
        ending: EndingDef,
        unresolved_count: int,
    ) -> bool:
        conds = ending.conditions
        for req_obj in conds.get("objectives_required", []):
            if req_obj not in state.completed_objectives:
                return False
        if "max_suspicion" in conds and state.suspicion > int(conds["max_suspicion"]):
            return False
        if "min_suspicion" in conds and state.suspicion < int(conds["min_suspicion"]):
            return False
        if "interrogations_allowed" in conds and state.interrogations_triggered > int(
            conds["interrogations_allowed"]
        ):
            return False
        if "unresolved_contradictions" in conds and unresolved_count > int(
            conds["unresolved_contradictions"]
        ):
            return False
        return True
