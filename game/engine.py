"""Core deterministic game engine orchestrating scenario, memory, and LLM layers."""

import re
import time
from typing import Any, Callable, Optional

from game.endings import EndingEvaluator
from game.interrogation import (
    INTERROGATION_SCENE_IMAGE,
    INTERROGATOR_GUARD,
    InterrogationManager,
)
from game.inventory import InventoryManager
from game.routes import RouteManager
from game.state import GameState, ItemUseResult, MoveResult, PenaltyRecord, TurnResult
from game.suspicion import SuspicionManager
from llm import get_client
from memory.models import Claim, Turn
from memory.store import MemoryStore
from scenario.loader import EndingDef, GuardDef, ScenarioConfig, load_scenario

# Slots that represent core visitor registration claims logged to security reports.
_REPORTABLE_IDENTITY_SLOTS = frozenset(
    {"name", "occupation", "employer", "reason_for_visit"}
)

_PAST_ITEM_PATTERN = re.compile(
    r"\b(?:already|earlier|before|just)\s+(?:showed|presented|handed|gave|used|submitted|flashed)\b",
    re.IGNORECASE,
)
_PAST_CLEARANCE_PATTERN = re.compile(
    r"\b(?:cleared|approved|authorized|let\s+me\s+(?:in|through|pass)|signed\s+off)\b",
    re.IGNORECASE,
)


class GameEngine:
    """Authoritative backend engine for Bobbery Rob.

    Owns all protected game state: suspicion, inventory, locations, routes,
    objectives, interrogations, and endings. The LLM only interprets player
    dialogue and generates character speech from backend-confirmed outcomes.
    """

    def __init__(
        self,
        scenario: Optional[ScenarioConfig] = None,
        llm_client: Any = None,
        memory: Optional[MemoryStore] = None,
        state: Optional[GameState] = None,
        *,
        player_id: Optional[str] = None,
        codename: Optional[str] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.scenario = scenario if scenario is not None else load_scenario()
        self.llm = llm_client if llm_client is not None else get_client()
        self.memory = memory if memory is not None else MemoryStore()
        self._clock = clock

        self.suspicion = SuspicionManager(self.scenario.suspicion_settings)
        self.inventory = InventoryManager(self.scenario)
        self.routes = RouteManager(self.scenario)
        self.interrogation = InterrogationManager(self.scenario, self.suspicion)
        self.endings = EndingEvaluator(self.scenario)

        if state is not None:
            self.state = state
        else:
            start_loc = self.scenario.starting_location
            start_guard = self.routes.guard_for_location(start_loc)
            self.state = GameState(
                scenario_id=self.scenario.scenario_id,
                current_location=start_loc,
                suspicion=self.suspicion.starting_value,
                inventory=self.inventory.initial_quantities(),
                visited_locations=[start_loc],
                active_speaker=start_guard.name,
                active_dialogue=start_guard.opening_line,
                started_at=self._clock(),
                player_id=player_id,
                codename=codename,
            )

    # ------------------------------------------------------------------ helpers

    @property
    def active_guard(self) -> GuardDef:
        if self.state.interrogation.is_final:
            return INTERROGATOR_GUARD
        return self.routes.guard_for_location(self.state.current_location)

    @property
    def current_scene_image(self) -> str:
        if self.state.interrogation.is_final:
            return INTERROGATION_SCENE_IMAGE
        return self.scenario.locations[self.state.current_location].image

    def elapsed_seconds(self) -> float:
        end_time = self.state.ended_at if self.state.ended_at is not None else self._clock()
        return max(0.0, float(end_time - self.state.started_at))

    # ------------------------------------------------------------- context prep

    def build_llm_context(
        self,
        current_turn_id: Optional[int] = None,
        extra_claim_ids: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        """Build the grounded context dictionary passed to `llm` prompt builders."""
        guard = self.active_guard
        location = self.scenario.locations[self.state.current_location]
        view = self.memory.guard_view(guard.id)

        # Combine claims this guard witnessed directly + claims tied to shared
        # security reports visible to this guard (visitor check-in logs, flags).
        claims_by_id: dict[int, Claim] = {c.id: c for c in view["claims"]}

        report_turns = {r.source_turn for r in view["reports"]}
        if report_turns:
            for slot in (
                "name",
                "occupation",
                "employer",
                "hometown",
                "reason_for_visit",
                "relationships",
                "other",
            ):
                for claim in self.memory.claims_in_slot(slot):
                    if claim.source_turn in report_turns:
                        claims_by_id[claim.id] = claim

        if extra_claim_ids:
            for cid in extra_claim_ids:
                try:
                    claims_by_id[cid] = self.memory.get_claim(cid)
                except KeyError:
                    continue

        earlier_claims = sorted(claims_by_id.values(), key=lambda c: c.id)
        evidence_turns: list[Turn] = (
            self.memory.evidence([c.id for c in earlier_claims]) if earlier_claims else []
        )

        # Also include interrogation evidence turns if active
        if self.state.interrogation.evidence_turn_ids:
            seen_ids = {t.turn_id for t in evidence_turns}
            for tid in self.state.interrogation.evidence_turn_ids:
                if tid not in seen_ids:
                    try:
                        evidence_turns.append(self.memory.get_turn(tid))
                        seen_ids.add(tid)
                    except KeyError:
                        continue

        recent_turns = view["turns"][-8:] if view["turns"] else self.memory.recent_turns(4)

        return {
            "guard": guard.to_dict(),
            "location": {"id": location.id, "name": location.name},
            "suspicion_label": self.suspicion.label_for(self.state.suspicion),
            "interrogation": self.interrogation.is_awaiting_explanation(self.state),
            "inventory": self.inventory.serialize_for_llm(self.state),
            "earlier_claims": earlier_claims,
            "evidence": evidence_turns,
            "recent_turns": recent_turns,
            "reports": view["reports"],
            "current_turn_id": current_turn_id,
        }

    # ------------------------------------------------------------ core actions

    def submit_message(self, player_text: str) -> TurnResult:
        """Process one natural-language player turn through the 2-step pipeline."""
        text = (player_text or "").strip()
        guard = self.active_guard
        susp_before = self.state.suspicion

        if self.state.ended:
            return self._rejected_turn(
                "The mission has already concluded.", guard, susp_before
            )
        if not text:
            return self._rejected_turn(
                "Type a response before sending.", guard, susp_before
            )

        # 1. Always archive player's verbatim words first
        player_turn = self.memory.add_turn(
            speaker="player",
            text=text,
            guard_id=guard.id,
            location_id=self.state.current_location,
        )
        self.state.guard_turns_count[guard.id] = (
            self.state.guard_turns_count.get(guard.id, 0) + 1
        )
        self.state.last_notice = None

        context = self.build_llm_context(current_turn_id=player_turn.turn_id)

        # 2. Branch: explanation evaluation (interrogation or pending discrepancy)
        if self.interrogation.is_awaiting_explanation(self.state):
            return self._handle_explanation_turn(text, player_turn, guard, context, susp_before)

        # 3. Branch: normal conversation (Call A -> Backend Rules -> Call B)
        return self._handle_normal_turn(text, player_turn, guard, context, susp_before)

    def use_item(self, item_id: str) -> ItemUseResult:
        """Validate and execute direct item presentation from the UI."""
        guard = self.active_guard
        if self.state.ended:
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=self.state.inventory.get(item_id, 0),
                suspicion_delta=0,
                dialogue=self.state.active_dialogue,
                notice="The mission has already concluded.",
            )

        result = self.inventory.use_item(
            self.state, item_id, guard, self.state.current_location
        )

        # Rejected (unowned or wrong location): no suspicion or dialogue change
        if result.outcome == "rejected":
            self.state.last_notice = result.notice
            return result

        # Record action in archive
        item_name = self.scenario.items[item_id].name
        player_turn = self.memory.add_turn(
            speaker="player",
            text=f"[Presented {item_name}]",
            guard_id=guard.id,
            location_id=self.state.current_location,
        )

        # Apply validated suspicion delta
        new_susp, applied_delta = self.suspicion.apply_delta(
            self.state.suspicion, result.suspicion_delta
        )
        self.state.suspicion = new_susp
        result.suspicion_delta = applied_delta

        # Track failure penalty and shared report on failed item attempts
        if result.outcome == "failure":
            self.state.penalties.append(
                PenaltyRecord(label="Failed Access Penalty", seconds=30)
            )
            self.memory.add_report(
                source_turn=player_turn.turn_id,
                summary=f"Failed item presentation ({item_name}) to {guard.name}: {result.notice}",
                shared_with=[],
            )
        elif result.outcome == "success":
            self.memory.add_report(
                source_turn=player_turn.turn_id,
                summary=f"Player presented {item_name} to {guard.name}: accepted.",
                shared_with=[],
            )
            # Clear pending non-final suspicion hold if item succeeded strongly
            if not self.state.interrogation.is_final and self.state.suspicion < 60:
                self.state.interrogation.active = False
                self.state.interrogation.pending_contradiction_id = None

        self.state.active_speaker = guard.name
        self.state.active_dialogue = result.dialogue
        self.state.last_notice = result.notice

        self.memory.add_turn(
            speaker="guard",
            text=result.dialogue,
            guard_id=guard.id,
            location_id=self.state.current_location,
        )

        # Check suspicion=100 lockdown
        if self.suspicion.is_final_interrogation(self.state.suspicion):
            self.interrogation.trigger_interrogation(self.state, is_final=True)
        elif self.suspicion.is_mandatory_interrogation(self.state.suspicion) and result.outcome == "failure":
            self.interrogation.trigger_interrogation(
                self.state, is_final=False, reason=result.notice
            )

        # Evaluate checkpoint objective clearance from item use
        self._evaluate_location_clearance(
            guard=guard,
            item_result=result,
            substantive_turn=False,
            had_contradiction=False,
        )

        # Evaluate mission endings
        self._check_and_finalize_ending()
        return result

    def move_to(self, target_location: str) -> MoveResult:
        """Attempt to transition to `target_location` through backend route validation."""
        return self.routes.move_to(self.state, target_location)

    def trigger_voluntary_exit(self) -> Optional[EndingDef]:
        """Trigger the Alternate Ending if the player meets its conditions."""
        if not self.endings.can_voluntary_exit(self.state):
            self.state.last_notice = "You cannot conclude via academic exit right now."
            return None
        self.state.voluntary_exit = True
        return self._check_and_finalize_ending()

    def apply_suspicion_event(self, event_name: str) -> int:
        """Apply a named suspicion event directly and enforce threshold side effects."""
        new_susp, applied = self.suspicion.apply_event(self.state.suspicion, event_name)
        self.state.suspicion = new_susp
        if self.suspicion.is_final_interrogation(self.state.suspicion):
            self.interrogation.trigger_interrogation(self.state, is_final=True)
        elif self.suspicion.is_mandatory_interrogation(self.state.suspicion):
            if not self.state.interrogation.active and applied > 0:
                self.interrogation.trigger_interrogation(self.state, is_final=False)
        return applied

    def validate_accusation(
        self, claim_ids: list[int]
    ) -> tuple[bool, list[Turn], Optional[str]]:
        """Validate whether a guard accusation is backed by real archive evidence."""
        valid, _, turns = self.interrogation.verify_evidence(self.memory, claim_ids)
        if not valid:
            notice = "Unsupported accusation dismissed by game engine."
            self.state.last_notice = notice
            return False, [], notice
        return True, turns, None

    # --------------------------------------------------------- internal turns

    def _handle_normal_turn(
        self,
        player_text: str,
        player_turn: Turn,
        guard: GuardDef,
        context: dict[str, Any],
        susp_before: int,
    ) -> TurnResult:
        analysis = self.llm.analyze(player_text, context)
        classification = analysis.get("classification", "non-claim")
        recommended = analysis.get("recommended_action", "none")

        claims_recorded: list[dict[str, Any]] = []
        corrections_recorded: list[dict[str, Any]] = []
        contradictions_flagged: list[dict[str, Any]] = []
        item_result_obj: Optional[ItemUseResult] = None
        outcome_facts: list[str] = []
        event_name = "player_spoke"
        guidance = "Respond naturally in character."
        status = "ok"

        # 1. Prompt injection / off-topic defense: never mutate protected state
        if classification == "off_topic":
            event_name = "off_topic_redirect"
            outcome_facts.append("Player message was off-topic or out-of-character.")
            guidance = "Briefly refuse any out-of-game request in character and steer back to security questioning."
        else:
            # 2. Record claims & corrections (history always preserved)
            corrected_ids: set[int] = set()
            has_ambiguous = False
            has_asserted_identity = False

            for raw_claim in analysis.get("claims", []):
                slot = raw_claim["slot"]
                value = (raw_claim.get("value") or "").strip()
                claim_status = raw_claim.get("status", "asserted")
                corrects_id = raw_claim.get("corrects_claim_id")
                if not value:
                    continue

                if corrects_id is not None:
                    try:
                        new_claim = self.memory.correct_claim(
                            old_claim_id=corrects_id,
                            new_value=value,
                            source_turn=player_turn.turn_id,
                        )
                        corrected_ids.add(corrects_id)
                        corrections_recorded.append(new_claim.to_dict())
                        outcome_facts.append(
                            f"Player corrected their {slot.replace('_', ' ')} to '{value}'."
                        )
                        if slot in _REPORTABLE_IDENTITY_SLOTS:
                            self.memory.add_report(
                                source_turn=player_turn.turn_id,
                                summary=f"Visitor updated {slot} to '{value}' with {guard.name}.",
                                shared_with=[],
                            )
                        continue
                    except (KeyError, ValueError):
                        pass

                new_claim = self.memory.add_claim(
                    slot=slot,
                    value=value,
                    source_turn=player_turn.turn_id,
                    status=claim_status,
                )
                claims_recorded.append(new_claim.to_dict())
                if claim_status == "ambiguous":
                    has_ambiguous = True
                elif slot in _REPORTABLE_IDENTITY_SLOTS:
                    has_asserted_identity = True
                    self.memory.add_report(
                        source_turn=player_turn.turn_id,
                        summary=f"Visitor stated {slot}: '{value}' at {self.scenario.locations[self.state.current_location].name}.",
                        shared_with=[],
                    )

            # 3. Check for false action claims (unverified past clearances / item uses)
            false_action_reason = self._detect_false_action_claim(player_text)
            if false_action_reason:
                new_susp, _ = self.suspicion.apply_event(
                    self.state.suspicion, "false_action_claim"
                )
                self.state.suspicion = new_susp
                event_name = "false_action_claim"
                outcome_facts.append(false_action_reason)
                guidance = (
                    "Point out that security logs have no record of the claimed action or clearance."
                )
                self.state.last_notice = "Unverified action claim flagged by security logs."
                self.memory.add_report(
                    source_turn=player_turn.turn_id,
                    summary=f"Player made unverified action claim to {guard.name}: {false_action_reason}",
                    shared_with=[],
                )

            # 4. Verify & apply evidence-backed contradictions
            for raw_conflict in analysis.get("contradictions", []):
                earlier_id = raw_conflict["earlier_claim_id"]
                if classification == "correction" and earlier_id in corrected_ids:
                    continue
                record = self.interrogation.flag_contradiction(
                    self.state,
                    self.memory,
                    slot=raw_conflict["slot"],
                    new_value=raw_conflict["new_value"],
                    earlier_claim_id=earlier_id,
                    reason=raw_conflict["reason"],
                    guard_id=guard.id,
                    current_turn_id=player_turn.turn_id,
                )
                if record is not None:
                    contradictions_flagged.append(record.to_dict())
                    outcome_facts.append(
                        f"Earlier (turn {record.evidence_turn_ids[0]}) the player claimed "
                        f"{record.slot}='{record.earlier_value}'; now claimed '{record.new_value}'."
                    )

            if contradictions_flagged:
                # Apply contradiction suspicion penalty once per contradictory turn
                new_susp, _ = self.suspicion.apply_event(
                    self.state.suspicion, "contradiction"
                )
                self.state.suspicion = new_susp
                status = "contradiction_flagged"
                event_name = "contradiction_flagged"
                guidance = (
                    "Confront the player with the earlier recorded statement from the supplied evidence "
                    "and demand an explanation."
                )
                self.state.last_notice = (
                    "Contradiction detected! Explain the discrepancy to de-escalate."
                )
                if self.suspicion.is_final_interrogation(self.state.suspicion):
                    self.interrogation.trigger_interrogation(self.state, is_final=True)
                    status = "interrogation"
                elif (
                    self.suspicion.is_mandatory_interrogation(self.state.suspicion)
                    or recommended == "start_interrogation"
                ):
                    self.interrogation.trigger_interrogation(self.state, is_final=False)
                    status = "interrogation"

            # 5. Handle chat-expressed item use intent through backend validator
            item_intent = analysis.get("item_use_intent")
            if item_intent and not contradictions_flagged:
                item_result_obj = self.inventory.use_item(
                    self.state, item_intent, guard, self.state.current_location
                )
                if item_result_obj.outcome != "rejected":
                    new_susp, applied = self.suspicion.apply_delta(
                        self.state.suspicion, item_result_obj.suspicion_delta
                    )
                    self.state.suspicion = new_susp
                    item_result_obj.suspicion_delta = applied
                    if item_result_obj.outcome == "failure":
                        self.state.penalties.append(
                            PenaltyRecord(label="Failed Access Penalty", seconds=30)
                        )
                    event_name = f"item_use_{item_result_obj.outcome}"
                    outcome_facts.append(item_result_obj.notice)
                    self.state.last_notice = item_result_obj.notice
                    if self.suspicion.is_final_interrogation(self.state.suspicion):
                        self.interrogation.trigger_interrogation(self.state, is_final=True)
                        status = "interrogation"
                else:
                    outcome_facts.append(item_result_obj.notice)
                    self.state.last_notice = item_result_obj.notice

            # 6. Ambiguity & repeated evasion handling (no penalty for single ambiguity/refusal)
            if not contradictions_flagged and not false_action_reason:
                if has_ambiguous:
                    status = "clarification_requested"
                    event_name = "clarification_requested"
                    guidance = "The player was vague. Ask a concise clarifying question."
                    self.state.consecutive_evasions = 0
                elif (
                    recommended == "ask_followup"
                    and classification in ("non-claim", "question")
                    and not claims_recorded
                    and not corrections_recorded
                    and item_result_obj is None
                ):
                    self.state.consecutive_evasions += 1
                    if self.state.consecutive_evasions >= 2:
                        new_susp, _ = self.suspicion.apply_event(
                            self.state.suspicion, "repeated_evasion"
                        )
                        self.state.suspicion = new_susp
                        event_name = "repeated_evasion"
                        outcome_facts.append(
                            "Player repeatedly avoided answering direct security questions."
                        )
                        guidance = "Express irritation at their evasiveness and press for a direct answer."
                        self.state.last_notice = "Repeated evasion increased suspicion."
                        self.state.consecutive_evasions = 1
                        if self.suspicion.is_final_interrogation(self.state.suspicion):
                            self.interrogation.trigger_interrogation(self.state, is_final=True)
                            status = "interrogation"
                else:
                    self.state.consecutive_evasions = 0

            # 7. Evaluate objective clearance for this location
            substantive = (
                bool(claims_recorded or corrections_recorded or has_asserted_identity)
                and not has_ambiguous
                and not false_action_reason
            )
            newly_completed = self._evaluate_location_clearance(
                guard=guard,
                item_result=item_result_obj,
                substantive_turn=substantive,
                had_contradiction=bool(contradictions_flagged),
            )
            for obj_id in newly_completed:
                obj = self.scenario.objectives[obj_id]
                outcome_facts.append(f"Objective cleared: {obj.name}.")
                if not contradictions_flagged:
                    guidance = (
                        f"Acknowledge that the visitor cleared this check ({obj.name}) "
                        "and may proceed when ready."
                    )
        if classification == "off_topic":
            newly_completed = []

        # 8. Call B: generate guard's spoken line from backend-confirmed outcome
        if self.state.interrogation.is_final:
            guard_after = self.active_guard
            dialogue = self.state.active_dialogue
        else:
            guard_after = guard
            dialogue_outcome: dict[str, Any] = {
                "event": event_name,
                "facts": outcome_facts or ["No protected game state changed this turn."],
                "guidance": guidance,
            }
            if item_result_obj is not None and item_result_obj.outcome != "rejected":
                dialogue_outcome["item_result"] = {
                    "item_id": item_result_obj.item_id,
                    "outcome": item_result_obj.outcome,
                    "dialogue": item_result_obj.dialogue,
                }
            # Refresh context so Call B sees newly added evidence/reports
            dialogue_ctx = self.build_llm_context(current_turn_id=player_turn.turn_id)
            dialogue = self.llm.write_dialogue(player_text, dialogue_outcome, dialogue_ctx)

        self.state.active_speaker = guard_after.name
        self.state.active_dialogue = dialogue
        self.memory.add_turn(
            speaker="guard",
            text=dialogue,
            guard_id=guard_after.id,
            location_id=self.state.current_location,
        )

        # 9. Check endings
        ending = self._check_and_finalize_ending()
        if ending is not None:
            status = "ended"

        return TurnResult(
            status=status,
            guard_id=guard_after.id,
            guard_name=guard_after.name,
            dialogue=dialogue,
            suspicion_before=susp_before,
            suspicion_after=self.state.suspicion,
            suspicion_delta=self.state.suspicion - susp_before,
            suspicion_label=self.suspicion.label_for(self.state.suspicion),
            notice=self.state.last_notice,
            claims_recorded=claims_recorded,
            corrections_recorded=corrections_recorded,
            contradictions_flagged=contradictions_flagged,
            item_result=item_result_obj.to_dict() if item_result_obj else None,
            objectives_completed=newly_completed,
            interrogation_active=self.state.interrogation.active,
            interrogation_is_final=self.state.interrogation.is_final,
            ended=self.state.ended,
            ending_id=self.state.ending_id,
        )

    def _handle_explanation_turn(
        self,
        player_text: str,
        player_turn: Turn,
        guard: GuardDef,
        context: dict[str, Any],
        susp_before: int,
    ) -> TurnResult:
        eval_raw = self.llm.evaluate_explanation(player_text, context)
        eval_outcome = self.interrogation.apply_explanation_evaluation(
            self.state, eval_raw
        )
        verdict = eval_outcome["evaluation"]

        newly_completed: list[str] = []
        if verdict == "convincing" and not self.state.interrogation_failed:
            loc_guard = self.routes.guard_for_location(self.state.current_location)
            newly_completed = self._evaluate_location_clearance(
                guard=loc_guard,
                item_result=None,
                substantive_turn=True,
                had_contradiction=False,
                convincing_explanation=True,
            )

        guard_after = self.active_guard
        dialogue_outcome = {
            "event": f"explanation_{verdict}",
            "facts": [
                f"Explanation evaluated as {verdict}: {eval_outcome['reason']}",
            ],
            "guidance": (
                "Accept the explanation and allow the visitor to continue."
                if verdict == "convincing"
                else "Express skepticism in character."
                if verdict == "partially_convincing"
                else "Reject the explanation firmly as unconvincing."
            ),
        }
        dialogue_ctx = self.build_llm_context(current_turn_id=player_turn.turn_id)
        dialogue = self.llm.write_dialogue(player_text, dialogue_outcome, dialogue_ctx)

        self.state.active_speaker = guard_after.name
        self.state.active_dialogue = dialogue
        self.memory.add_turn(
            speaker="guard",
            text=dialogue,
            guard_id=guard_after.id,
            location_id=self.state.current_location,
        )

        ending = self._check_and_finalize_ending()
        status = (
            "ended"
            if ending is not None
            else "interrogation"
            if self.state.interrogation.active
            else "ok"
        )

        return TurnResult(
            status=status,
            guard_id=guard_after.id,
            guard_name=guard_after.name,
            dialogue=dialogue,
            suspicion_before=susp_before,
            suspicion_after=self.state.suspicion,
            suspicion_delta=self.state.suspicion - susp_before,
            suspicion_label=self.suspicion.label_for(self.state.suspicion),
            notice=self.state.last_notice,
            explanation_evaluation=eval_outcome,
            objectives_completed=newly_completed,
            interrogation_active=self.state.interrogation.active,
            interrogation_is_final=self.state.interrogation.is_final,
            ended=self.state.ended,
            ending_id=self.state.ending_id,
        )

    def _detect_false_action_claim(self, player_text: str) -> Optional[str]:
        """Detect verbal claims of past item presentations or guard clearances not in engine state."""
        lower = player_text.lower()

        # Check claimed past item presentation
        if _PAST_ITEM_PATTERN.search(lower):
            for item_id, item_def in self.scenario.items.items():
                if item_def.name.lower() in lower:
                    # Check if a specific guard was named
                    named_guard = self._find_named_guard(lower)
                    if named_guard is not None:
                        recorded = any(
                            entry["item_id"] == item_id
                            and entry["guard_id"] == named_guard.id
                            for entry in self.state.items_presented_log
                        )
                        if not recorded:
                            return (
                                f"{named_guard.name} never logged any {item_def.name.lower()} "
                                "from the player."
                            )
                    elif item_id not in self.state.items_used:
                        return (
                            f"No record exists that the player presented {item_def.name.lower()}."
                        )

        # Check claimed past clearance by a specific scenario guard
        if _PAST_CLEARANCE_PATTERN.search(lower):
            named_guard = self._find_named_guard(lower)
            if named_guard is not None and named_guard.id not in self.state.cleared_guards:
                return f"{named_guard.name} never logged clearance for the player."

        return None

    def _find_named_guard(self, lower_text: str) -> Optional[GuardDef]:
        for guard in self.scenario.guards.values():
            full_name = guard.name.lower()
            surname = full_name.split()[-1] if full_name.split() else ""
            if full_name in lower_text or (len(surname) >= 4 and re.search(rf"\b{re.escape(surname)}\b", lower_text)):
                return guard
        return None

    def _evaluate_location_clearance(
        self,
        *,
        guard: GuardDef,
        item_result: Optional[ItemUseResult],
        substantive_turn: bool,
        had_contradiction: bool,
        convincing_explanation: bool = False,
    ) -> list[str]:
        """Determine whether the player's action cleared the active location's objective."""
        if (
            had_contradiction
            or self.state.interrogation.active
            or self.state.interrogation_failed
            or self.state.suspicion >= 80
        ):
            return []

        loc_id = self.state.current_location
        obj = self.routes.objective_for_location(loc_id)
        if obj is None or obj.id in self.state.completed_objectives:
            return []

        item_succeeded = item_result is not None and item_result.outcome == "success"
        item_partial = item_result is not None and item_result.outcome == "partial_success"
        cleared = False

        if loc_id == "museum_entrance":
            # Reception clears once the player gives a cover story or valid credentials/bribe
            cleared = substantive_turn or item_succeeded or convincing_explanation
        elif loc_id == "main_hall":
            # Hallway clears on a coherent exchange or credential check
            cleared = (
                substantive_turn
                or item_succeeded
                or (item_partial and self.state.suspicion < 60)
                or convincing_explanation
            )
        elif loc_id == "security_checkpoint":
            # Physical security checkpoint: dialogue alone cannot unlock it!
            # Requires validated credential item OR surviving formal verification.
            cleared = item_succeeded or convincing_explanation
        elif loc_id == "restricted_area":
            # Archive custodian clears on access card or coherent/convincing exchange
            cleared = item_succeeded or substantive_turn or convincing_explanation
        elif loc_id == "vault_display":
            # Vault gatekeeper clears on bribe/access card or coherent/convincing exchange
            cleared = item_succeeded or substantive_turn or convincing_explanation

        if not cleared:
            return []

        self.routes.complete_objective(self.state, obj.id)
        if guard.id not in self.state.cleared_guards:
            self.state.cleared_guards.append(guard.id)

        # Passing the security checkpoint issues a curator Access Card if not held
        if loc_id == "security_checkpoint" and self.state.inventory.get("access_card", 0) == 0:
            if "access_card" in self.scenario.items:
                self.inventory.grant_item(self.state, "access_card", 1)
                self.state.last_notice = (
                    f"{self.state.last_notice} Acquired Access Card."
                    if self.state.last_notice
                    else "Security checkpoint cleared. Acquired Access Card."
                )

        return [obj.id]

    def _check_and_finalize_ending(self) -> Optional[EndingDef]:
        if self.state.ended and self.state.ending_id:
            return self.scenario.endings.get(self.state.ending_id)

        ending = self.endings.evaluate(self.state)
        if ending is not None:
            self.state.ended = True
            self.state.ending_id = ending.id
            self.state.ended_at = self._clock()
        return ending

    def _rejected_turn(
        self, notice: str, guard: GuardDef, susp_before: int
    ) -> TurnResult:
        return TurnResult(
            status="rejected",
            guard_id=guard.id,
            guard_name=guard.name,
            dialogue=self.state.active_dialogue,
            suspicion_before=susp_before,
            suspicion_after=self.state.suspicion,
            suspicion_delta=0,
            suspicion_label=self.suspicion.label_for(self.state.suspicion),
            notice=notice,
            interrogation_active=self.state.interrogation.active,
            interrogation_is_final=self.state.interrogation.is_final,
            ended=self.state.ended,
            ending_id=self.state.ending_id,
        )

    # --------------------------------------------------------- UI & results

    def get_ui_state(self) -> dict[str, Any]:
        """Return the full gameplay dictionary consumed by Streamlit screens.

        Never exposes the player's hidden identity record or full claim summary.
        """
        loc = self.scenario.locations[self.state.current_location]
        guard = self.active_guard
        return {
            "mission_summary": self.scenario.mission_briefing.get(
                "summary", self.scenario.summary
            ),
            "location": {
                "id": loc.id,
                "name": "Interrogation Room" if self.state.interrogation.is_final else loc.name,
                "image": INTERROGATION_SCENE_IMAGE if self.state.interrogation.is_final else loc.thumbnail,
            },
            "scene": {
                "background": self.current_scene_image,
                "portrait": guard.portrait,
            },
            "objectives": self.routes.serialize_objectives(self.state),
            "dialogue": {
                "speaker": self.state.active_speaker or guard.name,
                "text": self.state.active_dialogue or guard.opening_line,
            },
            "suspicion": {
                "value": self.state.suspicion,
                "label": self.suspicion.label_for(self.state.suspicion),
            },
            "inventory": self.inventory.serialize_for_ui(self.state),
            "notice": self.state.last_notice,
            "interrogation": {
                "active": self.state.interrogation.active,
                "is_final": self.state.interrogation.is_final,
                "evidence_quotes": list(self.state.interrogation.evidence_quotes),
                "discrepancy_summary": self.state.interrogation.discrepancy_summary,
            },
            "available_routes": self.routes.available_routes(self.state),
            "can_voluntary_exit": self.endings.can_voluntary_exit(self.state),
            "ended": self.state.ended,
            "ending_id": self.state.ending_id,
        }

    def get_result(
        self,
        personal_best_seconds: Optional[float] = None,
        is_new_record: bool = False,
    ) -> dict[str, Any]:
        """Return the debrief dictionary for `screens/results.py`."""
        ending = (
            self.scenario.endings.get(self.state.ending_id)
            if self.state.ending_id
            else self.endings.evaluate(self.state)
        )
        if ending is None:
            ending = self.scenario.endings["capture_failure"]
        return self.endings.build_result_payload(
            state=self.state,
            ending=ending,
            raw_seconds=self.elapsed_seconds(),
            personal_best_seconds=personal_best_seconds,
            is_new_record=is_new_record,
        )

    # --------------------------------------------------------- serialization

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "memory": self.memory.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        scenario: Optional[ScenarioConfig] = None,
        llm_client: Any = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> "GameEngine":
        state = GameState.from_dict(data["state"])
        memory = MemoryStore.from_dict(data["memory"])
        return cls(
            scenario=scenario,
            llm_client=llm_client,
            memory=memory,
            state=state,
            clock=clock,
        )
