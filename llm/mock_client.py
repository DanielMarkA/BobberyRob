"""Mock LLM client with the same interface as `LLMClient`. Makes no API calls.

Default replies are canned but slightly responsive: naming an inventory item
in the message (for example "here is my invitation letter") sets
`item_use_intent`. Pass `analysis=`, `evaluation=` or `dialogue=` to script
exact replies; they are validated against the same schemas as real replies.
"""

import copy
from typing import Any, Optional

from llm import prompts, schemas

_MOCK_LINES: dict[str, str] = {
    "casual": "Sure, sure. And what brings you in tonight?",
    "strict": "State your business and your credentials.",
    "observant": "Interesting. What time did you arrive, exactly?",
    "experienced": "I've been here thirty years. Who sent you?",
    "impatient": "Make it quick. What do you want?",
}


class MockLLMClient:
    """Offline stand-in for `LLMClient`."""

    def __init__(
        self,
        analysis: Optional[dict[str, Any]] = None,
        evaluation: Optional[dict[str, Any]] = None,
        dialogue: Optional[str] = None,
    ) -> None:
        self._analysis = analysis
        self._evaluation = evaluation
        self._dialogue = dialogue
        self.model = "mock"
        self.last_error: Optional[str] = None

    def analyze(self, player_message: str, context: dict[str, Any]) -> dict[str, Any]:
        if self._analysis is not None:
            data = copy.deepcopy(self._analysis)
        else:
            data = copy.deepcopy(schemas.FALLBACK_ANALYSIS)
            item_id = _mentioned_item(player_message, context)
            if item_id:
                data["classification"] = "item_use"
                data["item_use_intent"] = item_id
        errors = schemas.analysis_errors(data)
        if errors:
            self.last_error = "schema: " + "; ".join(errors[:3])
            return schemas.fallback_analysis()
        claim_ids, turn_ids, item_ids = prompts.known_ids(context)
        return schemas.ground_analysis(data, claim_ids, turn_ids, item_ids)

    def write_dialogue(
        self,
        player_message: str,
        outcome: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        if self._dialogue is not None:
            return schemas.clean_dialogue(self._dialogue) or schemas.FALLBACK_DIALOGUE
        item_line = (outcome.get("item_result") or {}).get("dialogue")
        if item_line:
            return item_line
        personality = prompts.normalize_context(context)["guard"].get("personality", "")
        return _MOCK_LINES.get(personality, schemas.FALLBACK_DIALOGUE)

    def evaluate_explanation(self, explanation: str, context: dict[str, Any]) -> dict[str, Any]:
        data = copy.deepcopy(self._evaluation) if self._evaluation is not None else {
            "evaluation": "partially_convincing",
            "reason": "Mock evaluation.",
            "evidence_turns": [],
        }
        errors = schemas.evaluation_errors(data)
        if errors:
            self.last_error = "schema: " + "; ".join(errors[:3])
            return schemas.fallback_evaluation()
        _, turn_ids, _ = prompts.known_ids(context)
        return schemas.ground_evaluation(data, turn_ids)


def _mentioned_item(message: str, context: dict[str, Any]) -> Optional[str]:
    text = (message or "").lower()
    for item in prompts.normalize_context(context)["inventory"]:
        name = str(item.get("name", "")).lower()
        if name and name in text:
            return item.get("id")
    return None
