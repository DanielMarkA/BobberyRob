"""JSON schemas, validation and safe fallbacks for LLM output.

The schemas are written in OpenAI strict mode: every object sets
additionalProperties to false and lists every field in `required`. Optional
values are expressed as a null union.

Validation has two steps:
1. `jsonschema` checks shape, types and enum values. A failure means the reply
   is unusable and the client retries or falls back.
2. Grounding checks drop anything that points at a claim, turn or item the
   model was never shown, so the model cannot invent past statements or items.
"""

import copy
from collections.abc import Iterable
from typing import Any

from jsonschema import Draft202012Validator

from memory.models import SLOTS

CLASSIFICATIONS: tuple[str, ...] = (
    "claim",
    "correction",
    "non-claim",
    "question",
    "item_use",
    "off_topic",
)

# The model may only propose these two. "corrected" and "disputed" are set by the engine.
CLAIM_STATUSES: tuple[str, ...] = ("asserted", "ambiguous")

RECOMMENDED_ACTIONS: tuple[str, ...] = (
    "none",
    "ask_followup",
    "flag_contradiction",
    "start_interrogation",
)

EVALUATIONS: tuple[str, ...] = (
    "convincing",
    "partially_convincing",
    "unconvincing",
)

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "classification",
        "claims",
        "contradictions",
        "evidence_turns",
        "item_use_intent",
        "recommended_action",
    ],
    "properties": {
        "classification": {"type": "string", "enum": list(CLASSIFICATIONS)},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slot", "value", "status", "corrects_claim_id"],
                "properties": {
                    "slot": {"type": "string", "enum": list(SLOTS)},
                    "value": {"type": "string"},
                    "status": {"type": "string", "enum": list(CLAIM_STATUSES)},
                    "corrects_claim_id": {"type": ["integer", "null"]},
                },
            },
        },
        "contradictions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slot", "new_value", "earlier_claim_id", "reason"],
                "properties": {
                    "slot": {"type": "string", "enum": list(SLOTS)},
                    "new_value": {"type": "string"},
                    "earlier_claim_id": {"type": "integer"},
                    "reason": {"type": "string"},
                },
            },
        },
        "evidence_turns": {"type": "array", "items": {"type": "integer"}},
        "item_use_intent": {"type": ["string", "null"]},
        "recommended_action": {"type": "string", "enum": list(RECOMMENDED_ACTIONS)},
    },
}

EVALUATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["evaluation", "reason", "evidence_turns"],
    "properties": {
        "evaluation": {"type": "string", "enum": list(EVALUATIONS)},
        "reason": {"type": "string"},
        "evidence_turns": {"type": "array", "items": {"type": "integer"}},
    },
}

FALLBACK_ANALYSIS: dict[str, Any] = {
    "classification": "non-claim",
    "claims": [],
    "contradictions": [],
    "evidence_turns": [],
    "item_use_intent": None,
    "recommended_action": "none",
}

# A failed call must not punish the player, so the fallback is the middle tier.
FALLBACK_EVALUATION: dict[str, Any] = {
    "evaluation": "partially_convincing",
    "reason": "Evaluation unavailable.",
    "evidence_turns": [],
}

FALLBACK_DIALOGUE = "Hold on a moment. Say that again?"

MAX_DIALOGUE_CHARS = 400

_ANALYSIS_VALIDATOR = Draft202012Validator(ANALYSIS_SCHEMA)
_EVALUATION_VALIDATOR = Draft202012Validator(EVALUATION_SCHEMA)


def analysis_errors(data: Any) -> list[str]:
    """Return readable schema errors for an analysis reply. Empty means valid."""
    return _errors(_ANALYSIS_VALIDATOR, data)


def evaluation_errors(data: Any) -> list[str]:
    """Return readable schema errors for an evaluation reply. Empty means valid."""
    return _errors(_EVALUATION_VALIDATOR, data)


def _errors(validator: Draft202012Validator, data: Any) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(data)
    ]


def fallback_analysis() -> dict[str, Any]:
    result = copy.deepcopy(FALLBACK_ANALYSIS)
    result["fallback"] = True
    return result


def fallback_evaluation() -> dict[str, Any]:
    result = copy.deepcopy(FALLBACK_EVALUATION)
    result["fallback"] = True
    return result


def ground_analysis(
    data: dict[str, Any],
    known_claim_ids: Iterable[int],
    known_turn_ids: Iterable[int],
    known_item_ids: Iterable[str],
) -> dict[str, Any]:
    """Drop references to claims, turns and items that were not in the prompt.

    `data` must already be schema-valid. Returns a new dict.
    """
    claim_ids = set(known_claim_ids)
    turn_ids = set(known_turn_ids)
    item_ids = set(known_item_ids)
    result = copy.deepcopy(data)

    for claim in result["claims"]:
        if claim["corrects_claim_id"] not in claim_ids:
            claim["corrects_claim_id"] = None

    result["contradictions"] = [
        c for c in result["contradictions"] if c["earlier_claim_id"] in claim_ids
    ]
    result["evidence_turns"] = _unique([t for t in result["evidence_turns"] if t in turn_ids])

    if result["item_use_intent"] not in item_ids:
        result["item_use_intent"] = None

    if result["recommended_action"] == "flag_contradiction" and not result["contradictions"]:
        result["recommended_action"] = "ask_followup"

    result["fallback"] = False
    return result


def ground_evaluation(data: dict[str, Any], known_turn_ids: Iterable[int]) -> dict[str, Any]:
    """Drop evidence turns that were not in the prompt. Returns a new dict."""
    turn_ids = set(known_turn_ids)
    result = copy.deepcopy(data)
    result["evidence_turns"] = _unique([t for t in result["evidence_turns"] if t in turn_ids])
    result["fallback"] = False
    return result


def clean_dialogue(text: str | None) -> str | None:
    """Trim a dialogue reply. Returns None when the reply is unusable."""
    if not isinstance(text, str):
        return None
    line = text.strip().strip('"').strip()
    if not line:
        return None
    if len(line) > MAX_DIALOGUE_CHARS:
        cut = line[:MAX_DIALOGUE_CHARS]
        end = max(cut.rfind("."), cut.rfind("?"), cut.rfind("!"))
        line = cut[: end + 1] if end > 0 else cut
    return line


def _unique(values: list[int]) -> list[int]:
    seen: set[int] = set()
    return [v for v in values if not (v in seen or seen.add(v))]
