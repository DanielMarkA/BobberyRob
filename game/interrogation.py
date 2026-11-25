"""Evidence-backed contradiction tracking and interrogation lifecycle."""

from typing import Any, Optional

from game.state import ContradictionRecord, GameState, PenaltyRecord
from game.suspicion import SuspicionManager
from memory.models import Claim, Turn
from memory.store import MemoryStore
from scenario.loader import GuardDef, ScenarioConfig

INTERROGATION_SCENE_IMAGE = "/app/static/images/interrogation_room.webp"
INTERROGATION_GUARD_PORTRAIT = "/app/static/images/interrogator.webp"

INTERROGATOR_GUARD = GuardDef(
    id="guard_interrogator",
    name="Chief Investigator",
    role="Security Interrogator",
    personality="impatient",
    assigned_location="museum_entrance",
    opening_line=(
        "Sit down. Security flagged serious contradictions in your visitor logs. "
        "Give me a clear explanation right now."
    ),
    style_note="Abrupt, relentless, demands direct verifiable explanations.",
    portrait=INTERROGATION_GUARD_PORTRAIT,
)


class InterrogationManager:
    """Manages evidence verification, discrepancy questioning, and interrogations."""

    def __init__(
        self,
        scenario: ScenarioConfig,
        suspicion: SuspicionManager,
    ) -> None:
        self._scenario = scenario
        self._suspicion = suspicion

    def verify_evidence(
        self,
        memory: MemoryStore,
        claim_ids: list[int],
    ) -> tuple[bool, list[Claim], list[Turn]]:
        """Verify that every referenced claim exists and maps to verbatim archive turns."""
        claims: list[Claim] = []
        valid_ids: list[int] = []
        for cid in claim_ids:
            try:
                claim = memory.get_claim(cid)
            except KeyError:
                continue
            claims.append(claim)
            valid_ids.append(cid)

        if not valid_ids:
            return False, [], []

        turns = memory.evidence(valid_ids)
        if not turns:
            return False, [], []

        return True, claims, turns

    def flag_contradiction(
        self,
        state: GameState,
        memory: MemoryStore,
        *,
        slot: str,
        new_value: str,
        earlier_claim_id: int,
        reason: str,
        guard_id: str,
        current_turn_id: int,
    ) -> Optional[ContradictionRecord]:
        """Record a contradiction only when backed by verbatim archive evidence.

        Returns None (and dismisses the accusation) if no backing evidence exists.
        """
        valid, claims, turns = self.verify_evidence(memory, [earlier_claim_id])
        if not valid or not claims:
            state.last_notice = "Unsupported accusation dismissed by game engine."
            return None

        earlier_claim = claims[0]
        memory.set_status(earlier_claim.id, "disputed")

        evidence_turn_ids = [t.turn_id for t in turns]
        evidence_quotes = [t.text for t in turns]

        next_id = len(state.contradictions) + 1
        record = ContradictionRecord(
            id=next_id,
            slot=slot,
            earlier_claim_id=earlier_claim.id,
            earlier_value=earlier_claim.value,
            new_value=new_value,
            reason=reason,
            evidence_turn_ids=evidence_turn_ids,
            evidence_quotes=evidence_quotes,
            guard_id=guard_id,
            turn_id=current_turn_id,
        )
        state.contradictions.append(record)

        # Log shared security report so all guards can reference this incident
        memory.add_report(
            source_turn=current_turn_id,
            summary=(
                f"Contradiction flagged on '{slot}': earlier claimed "
                f"'{earlier_claim.value}' (turn {earlier_claim.source_turn}), "
                f"now claimed '{new_value}'."
            ),
            shared_with=[],
        )

        # Stage discrepancy so next player turn is evaluated as an explanation
        state.interrogation.pending_contradiction_id = record.id
        state.interrogation.evidence_turn_ids = list(evidence_turn_ids)
        state.interrogation.evidence_quotes = list(evidence_quotes)
        state.interrogation.discrepancy_summary = (
            f"Earlier you stated your {slot.replace('_', ' ')} was "
            f"'{earlier_claim.value}', but now you said '{new_value}'."
        )

        # Add time penalty for contradiction
        state.penalties.append(PenaltyRecord(label="Contradiction Penalty", seconds=30))
        return record

    def trigger_interrogation(
        self,
        state: GameState,
        *,
        is_final: bool = False,
        reason: Optional[str] = None,
    ) -> None:
        """Activate formal or final interrogation and lock movement."""
        was_active = state.interrogation.active
        was_final = state.interrogation.is_final

        state.interrogation.active = True
        if is_final:
            state.interrogation.is_final = True
            state.interrogation.max_attempts = 2
            if not was_final:
                state.interrogation.attempts_used = 0
                state.active_speaker = INTERROGATOR_GUARD.name
                state.active_dialogue = INTERROGATOR_GUARD.opening_line
        elif not was_active:
            state.interrogation.attempts_used = 0

        if not was_active or (is_final and not was_final):
            state.interrogations_triggered += 1

        if reason:
            state.interrogation.discrepancy_summary = reason
        if is_final:
            state.last_notice = "Suspicion reached 100 — Final Interrogation triggered!"
        else:
            state.last_notice = "Security interrogation initiated. Explain yourself."

    def is_awaiting_explanation(self, state: GameState) -> bool:
        """True when the next player message should be evaluated via Call C."""
        return state.interrogation.active or (
            state.interrogation.pending_contradiction_id is not None
        )

    def apply_explanation_evaluation(
        self,
        state: GameState,
        evaluation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply backend suspicion and interrogation resolution rules for an explanation."""
        verdict = evaluation_result.get("evaluation", "partially_convincing")
        event_map = {
            "convincing": "convincing_explanation",
            "partially_convincing": "partially_convincing_explanation",
            "unconvincing": "unconvincing_explanation",
        }
        event_name = event_map.get(verdict, "partially_convincing_explanation")
        new_suspicion, applied_delta = self._suspicion.apply_event(
            state.suspicion, event_name
        )
        state.suspicion = new_suspicion

        pending = self._get_pending_contradiction(state)
        resolved = False

        if verdict == "convincing":
            resolved = True
            if pending is not None:
                pending.resolved = True
                pending.resolution_evaluation = "convincing"
            state.interrogation.active = False
            state.interrogation.is_final = False
            state.interrogation.pending_contradiction_id = None
            state.interrogation.attempts_used = 0
            state.interrogation.evidence_quotes = []
            state.interrogation.evidence_turn_ids = []
            state.interrogation.discrepancy_summary = ""
            state.last_notice = "Your explanation convinced security."
        elif verdict == "partially_convincing":
            if pending is not None:
                pending.resolution_evaluation = "partially_convincing"
            state.interrogation.attempts_used += 1
            if state.interrogation.is_final:
                if state.interrogation.attempts_used >= state.interrogation.max_attempts:
                    state.interrogation_failed = True
                    state.last_notice = "Final interrogation failed. You have been detained."
                else:
                    state.last_notice = "Partially convincing, but the investigator still doubts you. One chance left."
            else:
                # Non-final questioning: release pending hold unless suspicion hit 100
                if self._suspicion.is_final_interrogation(state.suspicion):
                    self.trigger_interrogation(state, is_final=True)
                else:
                    state.interrogation.active = False
                    state.interrogation.pending_contradiction_id = None
                    state.last_notice = "Guard remains wary, but lets you continue for now."
        else:  # unconvincing
            if pending is not None:
                pending.resolution_evaluation = "unconvincing"
            state.penalties.append(
                PenaltyRecord(label="Unconvincing Explanation Penalty", seconds=60)
            )
            state.interrogation.attempts_used += 1
            if state.interrogation.is_final:
                state.interrogation_failed = True
                state.last_notice = "Final interrogation failed. Cover blown."
            elif self._suspicion.is_final_interrogation(state.suspicion):
                self.trigger_interrogation(state, is_final=True)
            elif self._suspicion.is_mandatory_interrogation(state.suspicion):
                self.trigger_interrogation(state, is_final=False)
            else:
                state.interrogation.pending_contradiction_id = None
                state.last_notice = "Unconvincing explanation raised suspicion."

        return {
            "evaluation": verdict,
            "reason": evaluation_result.get("reason", ""),
            "evidence_turns": list(evaluation_result.get("evidence_turns", [])),
            "suspicion_delta": applied_delta,
            "interrogation_resolved": resolved,
            "interrogation_failed": state.interrogation_failed,
        }

    def _get_pending_contradiction(
        self, state: GameState
    ) -> Optional[ContradictionRecord]:
        cid = state.interrogation.pending_contradiction_id
        if cid is None:
            return None
        for record in state.contradictions:
            if record.id == cid:
                return record
        return None
