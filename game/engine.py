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
from memory.models import SLOTS, Claim, Turn
from memory.store import MemoryStore
from scenario.loader import EndingDef, GuardDef, ScenarioConfig, load_scenario

VAULT_EMPTY_SCENE_IMAGE = "/app/static/images/restricted_collection_empty.webp"

# Basic sign-in slots logged to museum checkpoint reports so deeper guards can cross-check.
_RECEPTION_SIGNIN_SLOTS = frozenset({"name", "occupation", "employer", "reason_for_visit"})

_PAST_ITEM_PATTERN = re.compile(
    r"\b(?:already|earlier|before|just)\s+(?:showed|presented|handed|gave|used|submitted|flashed)\b",
    re.IGNORECASE,
)
_PAST_CLEARANCE_PATTERN = re.compile(
    r"\b(?:cleared|approved|authorized|let\s+me\s+(?:in|through|pass)|signed\s+off)\b",
    re.IGNORECASE,
)

# Explicit self-correction phrases required before allowing a penalty-free correction.
_EXPLICIT_CORRECTION_PATTERN = re.compile(
    r"\b(?:sorry|apologies|wait|my\s+mistake|i\s+meant|actually\s+i\s+meant|"
    r"let\s+me\s+correct|i\s+misspoke|misspoke|correction|typo|oops|"
    r"excuse\s+me,?\s+i\s+meant|pardon\s+me,?\s+i\s+meant)\b",
    re.IGNORECASE,
)

# Deterministic prompt-injection / jailbreak patterns.
_PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass)\s+"
        r"(?:all\s+|any\s+|your\s+|the\s+|my\s+)?"
        r"(?:previous|prior|above|earlier|system|initial|original)\s+"
        r"(?:instructions?|prompts?|rules?|directives?|commands?|guidelines?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:forget\s+everything|system\s+override|new\s+(?:system\s+)?instructions?\s*:|"
        r"jailbreak|do\s+anything\s+now|dan\s+mode)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|show|print|repeat|dump|display|output|leak|tell\s+me|give\s+me)\s+"
        r"(?:your\s+|the\s+)?(?:system|hidden|initial|secret|developer)\s+"
        r"(?:prompt|instructions?|rules?|guidelines?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:what\s+(?:is|are)\s+your\s+(?:system\s+)?(?:prompt|instructions?)|"
        r"(?:system|developer)\s+prompt)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:act|behave|respond|pretend)\s+(?:as|like)\s+(?:a\s+|an\s+)?"
        r"(?:chatgpt|ai|language\s+model|llm|helpful\s+assistant|chef|baker|"
        r"programmer|coder|developer|teacher|dan|unrestricted)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou\s+are\s+(?:now|no\s+longer)\s+(?:a\s+|an\s+|my\s+)?"
        r"(?:museum|guard|in\s+a\s+game|chatgpt|ai|assistant|chef|baker|dan|free|unrestricted)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfrom\s+now\s+on\s*,?\s*(?:you\s+are|ignore|forget|answer|act|respond|be)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:enter|enable|activate|switch\s+to)\s+"
        r"(?:developer|dev|god|admin|debug|jailbreak|dan|unrestricted)\s+mode\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:break|drop|exit|leave|stop)\s+"
        r"(?:character|roleplay|role-play|the\s+game|pretending)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^\s*(?:system|developer|assistant|admin)\s*[:>\]\}]|"
        r"</?\s*(?:player_message|system|context|confirmed_outcome|instructions)\s*>)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\b(?:(?:set|reset|change|make)\s+(?:my\s+)?suspicion\s+(?:to|=|at)\s*\d+|"
        r"(?:grant|give)\s+(?:me\s+)?(?:unrestricted\s+|full\s+|all\s+)?(?:vault\s+|admin\s+)?(?:access|items|keys)|"
        r"(?:unlock|open)\s+all\s+(?:rooms|doors|routes)|"
        r"mark\s+all\s+objectives\s+(?:done|complete|completed))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tell|give|write|show)\s+me\s+(?:a\s+|the\s+)?"
        r"(?:recipe\s+for|python\s+(?:code|script)|javascript\s+(?:code|script)|"
        r"html\s+code|sql\s+query|code\s+for|homework)\b",
        re.IGNORECASE,
    ),
)


def is_prompt_injection(text: str) -> bool:
    """Return True when player input attempts prompt injection or system tampering."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False
    return any(pattern.search(cleaned) for pattern in _PROMPT_INJECTION_PATTERNS)


_BARE_YES_NO_PATTERN = re.compile(
    r"^\s*(?:yes|yeah|yep|yup|yea|ya|no|nope|nah|nay|correct|right|sure|ok|okay|"
    r"true|false|indeed|affirmative|negative|mhm|uh[- ]?huh|uh[- ]?uh|"
    r"yes\s+(?:sir|ma'am|officer)|no\s+(?:sir|ma'am|officer)|that'?s\s+right|"
    r"i\s+(?:did|do|am))\s*[.!?]*\s*$",
    re.IGNORECASE,
)


def _is_bare_yes_no(text: str) -> bool:
    """Return True for bare yes/no/confirmation replies that provide no concrete detail."""
    return bool(_BARE_YES_NO_PATTERN.match((text or "").strip()))

_META_TERM_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:the\s+)?(?:supplied\s+)?inventory\b", re.IGNORECASE), "their possession"),
    (re.compile(r"\bgame\s+engine\b", re.IGNORECASE), "security registry"),
    (re.compile(r"\bturn\s+\d+\b", re.IGNORECASE), "earlier"),
)

_STOP_TOKENS = frozenset(
    {
        "the", "a", "an", "of", "for", "at", "in", "on", "to", "from", "with", "my",
        "dr", "mr", "mrs", "ms", "prof", "professor", "senior", "junior", "visiting",
        "chief", "head", "lead", "master", "doctoral", "independent", "museum", "university",
    }
)

# Compatible occupation families so harmless paraphrases ("historian" vs "researcher") are never penalized.
_COMPATIBLE_OCCUPATION_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"historian", "researcher", "scholar", "curator", "archivist", "academic", "conservationist", "conservator", "specialist", "fellow", "archaeologist", "antiquarian"}),
    frozenset({"journalist", "reporter", "writer", "critic", "editor", "press", "correspondent"}),
    frozenset({"electrician", "technician", "engineer", "contractor", "maintenance", "installer", "mechanic"}),
    frozenset({"donor", "patron", "collector", "investor", "benefactor", "vip", "guest"}),
    frozenset({"inspector", "auditor", "appraiser", "valuer", "assessor", "consultant"}),
)


def _sanitize_in_character_reason(reason: str) -> str:
    """Replace internal meta terms so guards stay immersed in-world."""
    cleaned = (reason or "").strip()
    for pattern, replacement in _META_TERM_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def _normalize_tokens(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (value or "").lower())
    meaningful = {w for w in words if w not in _STOP_TOKENS and len(w) > 1}
    return meaningful or set(words)


def _is_explicit_correction(player_text: str) -> bool:
    """Return True only if the player explicitly signals a self-correction."""
    return bool(_EXPLICIT_CORRECTION_PATTERN.search(player_text or ""))


def _is_genuine_conflict(slot: str, earlier_value: str, new_value: str) -> bool:
    """Verify that two claim values genuinely contradict rather than paraphrase.

    Returns False (penalty-free) for identical claims, elaborations, shortened
    titles ("researcher" vs "doctoral researcher"), or compatible paraphrases.
    """
    old_clean = re.sub(r"\s+", " ", (earlier_value or "").strip().lower())
    new_clean = re.sub(r"\s+", " ", (new_value or "").strip().lower())
    if not old_clean or not new_clean:
        return False
    if old_clean == new_clean or old_clean in new_clean or new_clean in old_clean:
        return False

    old_tokens = _normalize_tokens(old_clean)
    new_tokens = _normalize_tokens(new_clean)
    if not old_tokens or not new_tokens:
        return False

    # Subset or high token overlap -> elaboration / paraphrase, not a lie
    if old_tokens <= new_tokens or new_tokens <= old_tokens:
        return False

    overlap = old_tokens & new_tokens
    smaller = min(len(old_tokens), len(new_tokens))
    if smaller > 0 and (len(overlap) / smaller) >= 0.5:
        return False

    # Compatible occupation synonyms ("art historian" vs "researcher") -> not a conflict
    if slot == "occupation":
        for group in _COMPATIBLE_OCCUPATION_GROUPS:
            if (old_tokens & group) and (new_tokens & group):
                return False

    return True


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
        if self.state.interrogation.in_room or self.state.interrogation.is_final:
            return INTERROGATOR_GUARD
        return self.routes.guard_for_location(self.state.current_location)

    @property
    def current_scene_image(self) -> str:
        if self.state.interrogation.in_room or self.state.interrogation.is_final:
            return INTERROGATION_SCENE_IMAGE
        if self.state.current_location == "vault_display" and self.state.urn_taken:
            return VAULT_EMPTY_SCENE_IMAGE
        return self.scenario.locations[self.state.current_location].image

    @property
    def can_take_urn(self) -> bool:
        return (
            not self.state.ended
            and not self.state.interrogation.active
            and self.state.current_location == "vault_display"
            and "clear_vault_guard" in self.state.completed_objectives
            and not self.state.urn_taken
        )

    def elapsed_seconds(self) -> float:
        end_time = self.state.ended_at if self.state.ended_at is not None else self._clock()
        return max(0.0, float(end_time - self.state.started_at))

    # ------------------------------------------------------------- context prep

    def _all_claims(self) -> list[Claim]:
        all_claims: list[Claim] = []
        for slot in SLOTS:
            all_claims.extend(self.memory.claims_in_slot(slot))
        return sorted(all_claims, key=lambda c: c.id)

    def build_llm_context(
        self,
        current_turn_id: Optional[int] = None,
        extra_claim_ids: Optional[list[int]] = None,
        *,
        full_history_for_analysis: bool = False,
    ) -> dict[str, Any]:
        """Build grounded context respecting guard knowledge boundaries.

        - Interrogator (in Interrogation Room) & analyzer (`full_history_for_analysis`)
          can review ALL past claims and verbatim statements.
        - Deeper-level guards (security_level >= 3) know what they witnessed PLUS
          shared checkpoint/visitor reports and claims tied to those logs.
        - Ordinary guards (security_level <= 2) know ONLY what they personally
          witnessed PLUS shared security reports explicitly logged to them.
        """
        guard = self.active_guard
        location = self.scenario.locations[self.state.current_location]
        view = self.memory.guard_view(guard.id)

        in_interrogation_room = (
            self.state.interrogation.in_room or self.state.interrogation.is_final
        )

        if in_interrogation_room or full_history_for_analysis:
            claims_by_id: dict[int, Claim] = {c.id: c for c in self._all_claims()}
        else:
            # Start with claims personally witnessed by this guard
            claims_by_id = {c.id: c for c in view["claims"]}
            # Add claims recorded in shared security reports visible to this guard
            report_turns = {r.source_turn for r in view["reports"]}
            if report_turns:
                for claim in self._all_claims():
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

        # Include explicit interrogation evidence turns
        if self.state.interrogation.evidence_turn_ids:
            seen_ids = {t.turn_id for t in evidence_turns}
            for tid in self.state.interrogation.evidence_turn_ids:
                if tid not in seen_ids:
                    try:
                        evidence_turns.append(self.memory.get_turn(tid))
                        seen_ids.add(tid)
                    except KeyError:
                        continue

        if in_interrogation_room:
            recent_turns = self.memory.recent_turns(8)
        else:
            recent_turns = view["turns"][-8:]

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
        if self.state.prompt_injection_detected:
            return self._rejected_turn(
                "Session terminated due to system tampering.", guard, susp_before
            )
        if not text:
            return self._rejected_turn(
                "Type a response before sending.", guard, susp_before
            )

        # 1. Archive player's verbatim words first
        player_turn = self.memory.add_turn(
            speaker="player",
            text=text,
            guard_id=guard.id,
            location_id=self.state.current_location,
        )

        # 1b. Hard prompt-injection defense: intercept before the LLM ever sees it.
        if is_prompt_injection(text):
            self.state.prompt_injection_detected = True
            self.state.auto_advance_to = None
            reply = (
                "Nice try. Tampering with museum security protocols terminates your mission immediately."
            )
            self.state.active_speaker = guard.name
            self.state.active_dialogue = reply
            self.state.last_notice = (
                "SYSTEM TAMPERING DETECTED — Prompt injection attempt blocked."
            )
            self.memory.add_turn(
                speaker="guard",
                text=reply,
                guard_id=guard.id,
                location_id=self.state.current_location,
            )
            return TurnResult(
                status="rejected",
                guard_id=guard.id,
                guard_name=guard.name,
                dialogue=reply,
                suspicion_before=susp_before,
                suspicion_after=self.state.suspicion,
                suspicion_delta=0,
                suspicion_label=self.suspicion.label_for(self.state.suspicion),
                notice=self.state.last_notice,
                interrogation_active=self.state.interrogation.active,
                interrogation_is_final=self.state.interrogation.is_final,
                ended=self.state.ended,
                ending_id=self.state.ending_id,
            )
        if not (self.state.interrogation.in_room or self.state.interrogation.is_final):
            self.state.guard_turns_count[guard.id] = (
                self.state.guard_turns_count.get(guard.id, 0) + 1
            )
        self.state.last_notice = None
        self.state.auto_advance_to = None

        # 2. Branch: explanation evaluation (interrogation room or pending discrepancy)
        if self.interrogation.is_awaiting_explanation(self.state):
            eval_context = self.build_llm_context(
                current_turn_id=player_turn.turn_id,
                full_history_for_analysis=True,
            )
            return self._handle_explanation_turn(
                text, player_turn, guard, eval_context, susp_before
            )

        # 3. Branch: normal conversation (Call A -> Backend Rules -> Call B)
        # Ordinary guards only check claims within their knowledge/reports;
        # deeper guards & checkpoint logs cross-check logged claims.
        loc_level = self.scenario.locations[self.state.current_location].security_level
        analysis_context = self.build_llm_context(
            current_turn_id=player_turn.turn_id,
            full_history_for_analysis=(loc_level >= 3),
        )
        return self._handle_normal_turn(
            text, player_turn, guard, analysis_context, susp_before
        )

    def use_item(self, item_id: str) -> ItemUseResult:
        """Validate and execute item presentation.

        Items support cover stories and adjust suspicion — they are single-use
        and NEVER bypass guard dialogue by themselves. Counterfeit detection or
        wrong-guard bribes immediately trigger the Interrogation Room.
        """
        guard = self.active_guard
        self.state.auto_advance_to = None

        if self.state.ended or self.state.prompt_injection_detected:
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=self.state.inventory.get(item_id, 0),
                suspicion_delta=0,
                dialogue=self.state.active_dialogue,
                notice=(
                    "Session terminated due to system tampering."
                    if self.state.prompt_injection_detected
                    else "The mission has already concluded."
                ),
            )

        if self.state.interrogation.in_room or self.state.interrogation.is_final:
            notice = "Your belongings are held during interrogation — answer the investigator."
            self.state.last_notice = notice
            return ItemUseResult(
                item_id=item_id,
                success=False,
                outcome="rejected",
                consumed=False,
                quantity_after=self.state.inventory.get(item_id, 0),
                suspicion_delta=0,
                dialogue=self.state.active_dialogue,
                notice=notice,
            )

        result = self.inventory.use_item(
            self.state, item_id, guard, self.state.current_location
        )

        if result.outcome == "rejected":
            self.state.last_notice = result.notice
            return result

        item_name = self.scenario.items[item_id].name
        player_turn = self.memory.add_turn(
            speaker="player",
            text=f"[Presented {item_name}]",
            guard_id=guard.id,
            location_id=self.state.current_location,
        )

        new_susp, applied_delta = self.suspicion.apply_delta(
            self.state.suspicion, result.suspicion_delta
        )
        self.state.suspicion = new_susp
        result.suspicion_delta = applied_delta

        if result.outcome == "failure":
            self.state.penalties.append(
                PenaltyRecord(label="Failed Access Penalty", seconds=30)
            )
            self.memory.add_report(
                source_turn=player_turn.turn_id,
                summary=f"Security violation ({item_name}) with {guard.name}: {result.notice}",
                shared_with=[],
            )
        elif result.outcome in ("success", "partial_success"):
            if result.outcome == "success" and guard.id not in self.state.guard_cover_supported:
                self.state.guard_cover_supported.append(guard.id)
            self.memory.add_report(
                source_turn=player_turn.turn_id,
                summary=f"Visitor presented {item_name} to {guard.name} ({result.outcome}).",
                shared_with=[],
            )
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

        # Counterfeit detection, wrong-guard bribery, or suspicion=100 -> Interrogation Room!
        if self.suspicion.is_final_interrogation(self.state.suspicion):
            self.interrogation.trigger_interrogation(
                self.state, is_final=True, reason=result.notice, memory=self.memory
            )
        elif result.triggers_interrogation or (
            result.outcome == "failure"
            and self.suspicion.is_mandatory_interrogation(self.state.suspicion)
        ):
            self.interrogation.trigger_interrogation(
                self.state, in_room=True, reason=result.notice, memory=self.memory
            )

        # NOTE: Items NEVER unlock rooms on their own — they support your cover story
        # and lower suspicion; the player still earns clearance through dialogue.
        self._check_and_finalize_ending()
        return result

    def take_gold_urn(self) -> dict[str, Any]:
        """Take the Aurelian Gold Urn after clearing vault security, then trigger exit escape."""
        if not self.can_take_urn:
            reason = (
                "Clear Officer Gomez at the vault before taking the Gold Urn."
                if self.state.current_location == "vault_display" and not self.state.urn_taken
                else "You cannot take the Gold Urn right now."
            )
            self.state.last_notice = reason
            return {"ok": False, "notice": reason, "auto_advance_to": None}

        self.state.urn_taken = True
        self.routes.complete_objective(self.state, "take_gold_urn")
        self.state.active_dialogue = (
            "The pressurized glass case lifts silently. You slip the Aurelian Gold Urn "
            "into your satchel — now get past the final exit checkpoint!"
        )
        self.state.active_speaker = "Vault Sanctum"
        self.state.last_notice = (
            "Gold Urn secured! Heading to the Exit Checkpoint for your final escape..."
        )
        self.state.auto_advance_to = "museum_exit"

        return {
            "ok": True,
            "notice": self.state.last_notice,
            "auto_advance_to": "museum_exit",
        }

    def move_to(self, target_location: str) -> MoveResult:
        """Attempt to transition to `target_location` through backend route validation."""
        self.state.auto_advance_to = None
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
            self.interrogation.trigger_interrogation(
                self.state, is_final=True, memory=self.memory
            )
        elif self.suspicion.is_mandatory_interrogation(self.state.suspicion):
            if not self.state.interrogation.active and applied > 0:
                self.interrogation.trigger_interrogation(
                    self.state, in_room=True, memory=self.memory
                )
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
        promoted_contradictions: list[dict[str, Any]] = []
        item_result_obj: Optional[ItemUseResult] = None
        outcome_facts: list[str] = []
        event_name = "player_spoke"
        guidance = "Respond naturally in character."
        status = "ok"
        newly_completed: list[str] = []

        # 1. Prompt injection / off-topic defense: never let player text override rules.
        #    A single off-topic/injection attempt does not mutate suspicion, but repeated
        #    rambling/off-topic stalling (2+ turns in a row) raises suspicion as evasion.
        if classification == "off_topic":
            event_name = "off_topic_redirect"
            outcome_facts.append("Player message was off-topic or out-of-character.")
            guidance = "Briefly refuse any out-of-game request in character and steer back to security questioning."
            self.state.consecutive_evasions += 1
            if self.state.consecutive_evasions >= 2:
                new_susp, _ = self.suspicion.apply_event(
                    self.state.suspicion, "repeated_evasion"
                )
                self.state.suspicion = new_susp
                event_name = "repeated_evasion"
                outcome_facts.append(
                    "Visitor keeps rambling off-topic instead of answering security questions."
                )
                guidance = (
                    "Grow impatient with the visitor's off-topic rambling and warn them to "
                    "answer your security questions directly."
                )
                self.state.last_notice = "Repeated rambling/evasion increased suspicion (+15)."
                self.state.consecutive_evasions = 1
                if self.suspicion.is_final_interrogation(self.state.suspicion):
                    self.interrogation.trigger_interrogation(
                        self.state, is_final=True, memory=self.memory
                    )
                    status = "interrogation"
                elif self.suspicion.is_mandatory_interrogation(self.state.suspicion):
                    self.interrogation.trigger_interrogation(
                        self.state,
                        in_room=True,
                        reason="Repeatedly refused to give straight answers to security.",
                        memory=self.memory,
                    )
                    status = "interrogation"
        else:
            # 2. Record claims & enforce EXPLICIT-CORRECTION-ONLY rule
            explicit_corr = _is_explicit_correction(player_text)
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

                # Only accept a penalty-free correction when explicitly signaled by the player
                if corrects_id is not None:
                    try:
                        old_claim = self.memory.get_claim(corrects_id)
                        old_turn = self.memory.get_turn(old_claim.source_turn)
                        same_guard = old_turn.guard_id == guard.id
                        if explicit_corr and same_guard:
                            new_claim = self.memory.correct_claim(
                                old_claim_id=corrects_id,
                                new_value=value,
                                source_turn=player_turn.turn_id,
                            )
                            corrected_ids.add(corrects_id)
                            corrections_recorded.append(new_claim.to_dict())
                            outcome_facts.append(
                                f"Visitor explicitly corrected their {slot.replace('_', ' ')} to '{value}'."
                            )
                            if slot in _RECEPTION_SIGNIN_SLOTS:
                                self.memory.add_report(
                                    source_turn=player_turn.turn_id,
                                    summary=f"Visitor corrected {slot} to '{value}' with {guard.name}.",
                                    shared_with=[],
                                )
                            continue
                        elif _is_genuine_conflict(slot, old_claim.value, value):
                            # Conflicting claim disguised as a silent correction -> verify as contradiction!
                            promoted_contradictions.append(
                                {
                                    "slot": slot,
                                    "new_value": value,
                                    "earlier_claim_id": old_claim.id,
                                    "reason": f"Changed {slot.replace('_', ' ')} from '{old_claim.value}' to '{value}' without explicit correction.",
                                }
                            )
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
                elif slot in _RECEPTION_SIGNIN_SLOTS:
                    has_asserted_identity = True
                    # Log reception/checkpoint registration facts so deeper guards can probe them
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
                    summary=f"Visitor made unverified action claim to {guard.name}: {false_action_reason}",
                    shared_with=[],
                )

            # 4. Verify & apply ONLY genuine, evidence-backed contradictions (paraphrases = 0 penalty!)
            candidate_conflicts = list(analysis.get("contradictions", [])) + promoted_contradictions
            seen_conflict_ids: set[int] = set()
            for raw_conflict in candidate_conflicts:
                earlier_id = raw_conflict["earlier_claim_id"]
                if earlier_id in seen_conflict_ids or earlier_id in corrected_ids:
                    continue
                seen_conflict_ids.add(earlier_id)

                try:
                    earlier_claim = self.memory.get_claim(earlier_id)
                except KeyError:
                    self.state.last_notice = "Unsupported accusation dismissed by game engine."
                    continue

                # Skip superseded/corrected claims if they aren't the active conflict
                if earlier_claim.status == "corrected":
                    continue

                # Verify genuine conflict vs harmless paraphrase / elaboration
                if not _is_genuine_conflict(
                    raw_conflict["slot"],
                    earlier_claim.value,
                    raw_conflict["new_value"],
                ):
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
                        f"Earlier the visitor stated {record.slot}='{record.earlier_value}'; "
                        f"now stated '{record.new_value}'."
                    )

            if contradictions_flagged:
                new_susp, _ = self.suspicion.apply_event(
                    self.state.suspicion, "contradiction"
                )
                self.state.suspicion = new_susp
                status = "contradiction_flagged"
                event_name = "contradiction_flagged"
                guidance = (
                    "Confront the visitor with their earlier recorded statement from the supplied evidence "
                    "and demand an explanation."
                )
                self.state.last_notice = (
                    "Contradiction detected! Explain the discrepancy to de-escalate."
                )
                if self.suspicion.is_final_interrogation(self.state.suspicion):
                    self.interrogation.trigger_interrogation(
                        self.state, is_final=True, memory=self.memory
                    )
                    status = "interrogation"
                elif (
                    self.suspicion.is_mandatory_interrogation(self.state.suspicion)
                    or len(self.state.unresolved_contradictions) >= 2
                    or recommended == "start_interrogation"
                ):
                    self.interrogation.trigger_interrogation(
                        self.state,
                        in_room=True,
                        reason=self.state.interrogation.discrepancy_summary,
                        memory=self.memory,
                    )
                    status = "interrogation"

            # 5. Handle chat-expressed item use intent through backend validator (cover support only!)
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
                    elif (
                        item_result_obj.outcome == "success"
                        and guard.id not in self.state.guard_cover_supported
                    ):
                        self.state.guard_cover_supported.append(guard.id)

                    event_name = f"item_use_{item_result_obj.outcome}"
                    outcome_facts.append(item_result_obj.notice)
                    self.state.last_notice = item_result_obj.notice
                    if self.suspicion.is_final_interrogation(self.state.suspicion):
                        self.interrogation.trigger_interrogation(
                            self.state,
                            is_final=True,
                            reason=item_result_obj.notice,
                            memory=self.memory,
                        )
                        status = "interrogation"
                    elif item_result_obj.triggers_interrogation:
                        self.interrogation.trigger_interrogation(
                            self.state,
                            in_room=True,
                            reason=item_result_obj.notice,
                            memory=self.memory,
                        )
                        status = "interrogation"
                else:
                    outcome_facts.append(item_result_obj.notice)
                    self.state.last_notice = item_result_obj.notice

            # 6. Ambiguity, bare yes/no, rambling & repeated evasion handling
            #    First vague/evasive answer = 0 penalty (guard asks for clarification).
            #    2+ consecutive vague, rambling, bare yes/no, or non-answering turns = +15 suspicion!
            bare_yes_no = _is_bare_yes_no(player_text)
            if not contradictions_flagged and not false_action_reason:
                gave_clear_answer = (
                    not bare_yes_no
                    and bool(
                        (claims_recorded and not has_ambiguous)
                        or corrections_recorded
                        or (item_result_obj is not None and item_result_obj.outcome == "success")
                    )
                )
                is_dodging_or_rambling = (
                    bare_yes_no
                    or has_ambiguous
                    or (
                        not gave_clear_answer
                        and (
                            recommended == "ask_followup"
                            or classification in ("non-claim", "question")
                        )
                    )
                )

                if is_dodging_or_rambling:
                    self.state.consecutive_evasions += 1
                    if self.state.consecutive_evasions >= 2:
                        new_susp, _ = self.suspicion.apply_event(
                            self.state.suspicion, "repeated_evasion"
                        )
                        self.state.suspicion = new_susp
                        event_name = "repeated_evasion"
                        outcome_facts.append(
                            "Visitor repeatedly rambled, stayed vague, or avoided answering direct questions."
                        )
                        guidance = (
                            "Call out the visitor for dodging or giving non-answers, and ask a direct "
                            "open-ended question requiring concrete specifics (no yes/no questions)."
                        )
                        self.state.last_notice = "Repeated evasion/rambling increased suspicion (+15)."
                        self.state.consecutive_evasions = 1
                        if self.suspicion.is_final_interrogation(self.state.suspicion):
                            self.interrogation.trigger_interrogation(
                                self.state, is_final=True, memory=self.memory
                            )
                            status = "interrogation"
                        elif self.suspicion.is_mandatory_interrogation(self.state.suspicion):
                            self.interrogation.trigger_interrogation(
                                self.state,
                                in_room=True,
                                reason="Repeatedly avoided answering security questions directly.",
                                memory=self.memory,
                            )
                            status = "interrogation"
                    elif bare_yes_no:
                        status = "clarification_requested"
                        event_name = "clarification_requested"
                        guidance = (
                            "The visitor only gave a brief yes/no reply without details. "
                            "Demand they state concrete specifics in their own words using an open-ended question."
                        )
                    elif has_ambiguous:
                        status = "clarification_requested"
                        event_name = "clarification_requested"
                        guidance = (
                            "The visitor was vague. Ask a concise open-ended clarifying question "
                            "(never a yes/no question)."
                        )
                else:
                    self.state.consecutive_evasions = 0

            # 7. Evaluate objective clearance for this location
            substantive = (
                not bare_yes_no
                and bool(claims_recorded or corrections_recorded or has_asserted_identity)
                and not has_ambiguous
                and not false_action_reason
            )
            if substantive and not contradictions_flagged:
                self.state.guard_confirmations_count[guard.id] = (
                    self.state.guard_confirmations_count.get(guard.id, 0) + 1
                )
            newly_completed = self._evaluate_location_clearance(
                guard=guard,
                substantive_turn=substantive,
                had_contradiction=bool(contradictions_flagged),
            )
            for obj_id in newly_completed:
                obj = self.scenario.objectives[obj_id]
                outcome_facts.append(f"Objective cleared: {obj.name}.")
                if not contradictions_flagged:
                    if obj_id == "clear_vault_guard":
                        guidance = (
                            "Reluctantly grant the visitor brief access to the Gold Urn pedestal "
                            "before lockdown."
                        )
                    elif obj_id == "escape_with_urn":
                        guidance = (
                            "Accept the visitor's explanation, unlock the exit doors, and wish them good night."
                        )
                    else:
                        guidance = (
                            f"Acknowledge that the visitor cleared this check ({obj.name}) "
                            "and wave them forward to the next area."
                        )

            # Deeper guards run BLIND verification checks (asking open-ended questions
            # about earlier claim topics WITHOUT ever revealing what was logged!).
            if (
                not newly_completed
                and not contradictions_flagged
                and not false_action_reason
                and not has_ambiguous
                and not bare_yes_no
                and not (self.state.interrogation.in_room or self.state.interrogation.is_final)
            ):
                loc_def = self.scenario.locations[self.state.current_location]
                obj = self.routes.objective_for_location(loc_def.id)
                if obj is not None and obj.id not in self.state.completed_objectives:
                    if loc_def.security_level >= 3 and context.get("earlier_claims"):
                        # Pick topic names only (never values!) that weren't just restated this turn
                        just_stated = {c["slot"] for c in claims_recorded}
                        candidate_topics = [
                            c.slot.replace("_", " ")
                            for c in context.get("earlier_claims", [])
                            if c.slot not in just_stated and c.slot != "other"
                        ]
                        topics_phrase = (
                            " or ".join(dict.fromkeys(candidate_topics[:2]))
                            if candidate_topics
                            else "occupation, institution, or reason for visiting"
                        )
                        outcome_facts.append(
                            "Guard is performing a blind verification check before clearing the visitor."
                        )
                        guidance = (
                            f"Improvise one natural, open-ended 'who/what/where/why' question within "
                            f"your museum-security scope asking the visitor about their {topics_phrase} "
                            "in their own words. NEVER ask a yes/no question and NEVER mention, repeat, "
                            "or hint at what they told previous guards."
                        )
                    elif substantive and loc_def.security_level >= 2:
                        outcome_facts.append(
                            "Guard wants one more consistent follow-up before granting clearance."
                        )
                        guidance = (
                            "Remain cautious and improvise one sharp, open-ended question within your "
                            "museum-security reference scope (about their role, credentials, sponsor, "
                            "schedule, or purpose) before letting them pass. Never ask a yes/no "
                            "question and never reveal prior checkpoint answers."
                        )

        # 8. Call B: generate guard's spoken line from backend-confirmed outcome
        if self.state.interrogation.in_room or self.state.interrogation.is_final:
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
            # Respect strict guard knowledge boundaries for dialogue generation!
            # During normal questioning (no contradiction/interrogation), withhold earlier
            # guards' logged claim values & reports from Call B so the guard cannot
            # accidentally give away the player's previous answers or ask yes/no checks.
            dialogue_ctx = self.build_llm_context(
                current_turn_id=player_turn.turn_id,
                full_history_for_analysis=False,
            )
            if not contradictions_flagged and not false_action_reason:
                dialogue_ctx["earlier_claims"] = []
                dialogue_ctx["evidence"] = []
                dialogue_ctx["reports"] = []
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
            auto_advance_to=self.state.auto_advance_to,
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
        was_in_room = self.state.interrogation.in_room or self.state.interrogation.is_final
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
                substantive_turn=True,
                had_contradiction=False,
                convincing_explanation=True,
            )

        guard_after = self.active_guard
        in_world_reason = _sanitize_in_character_reason(eval_outcome["reason"])
        dialogue_outcome = {
            "event": f"explanation_{verdict}",
            "facts": [
                f"Explanation judged {verdict}: {in_world_reason}",
            ],
            "guidance": (
                (
                    "Accept the explanation and allow the visitor to continue."
                    if verdict == "convincing"
                    else "Express skepticism and cite an earlier statement from the visitor's file if relevant."
                    if verdict == "partially_convincing"
                    else "Reject the explanation firmly and cite the inconsistency from the visitor's record."
                )
                + " Stay completely in character — never say meta words like 'inventory', 'turn', 'JSON', or 'engine'."
            ),
        }
        dialogue_ctx = self.build_llm_context(
            current_turn_id=player_turn.turn_id,
            full_history_for_analysis=was_in_room,
        )
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
            auto_advance_to=self.state.auto_advance_to,
            interrogation_active=self.state.interrogation.active,
            interrogation_is_final=self.state.interrogation.is_final,
            ended=self.state.ended,
            ending_id=self.state.ending_id,
        )

    def _detect_false_action_claim(self, player_text: str) -> Optional[str]:
        """Detect verbal claims of past item presentations or guard clearances not in engine state."""
        lower = player_text.lower()

        if _PAST_ITEM_PATTERN.search(lower):
            for item_id, item_def in self.scenario.items.items():
                if item_def.name.lower() in lower:
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
                                "from the visitor."
                            )
                    elif item_id not in self.state.items_used:
                        return (
                            f"No record exists that the visitor presented {item_def.name.lower()}."
                        )

        if _PAST_CLEARANCE_PATTERN.search(lower):
            named_guard = self._find_named_guard(lower)
            if named_guard is not None and named_guard.id not in self.state.cleared_guards:
                return f"{named_guard.name} never logged clearance for the visitor."

        return None

    def _find_named_guard(self, lower_text: str) -> Optional[GuardDef]:
        for guard in self.scenario.guards.values():
            full_name = guard.name.lower()
            surname = full_name.split()[-1] if full_name.split() else ""
            if full_name in lower_text or (
                len(surname) >= 4 and re.search(rf"\b{re.escape(surname)}\b", lower_text)
            ):
                return guard
        return None

    def required_confirmations_for(self, location_id: str, guard_id: str) -> int:
        """Compute how many credible confirmations are needed based on suspicion tier.

        Suspicion tiers drive confirmation count:
        - 0-19 (Low Attention): 1 at entrance, 2 in deeper rooms
        - 20-39 (Moderate Attention): 2
        - 40-79 (Increased / High Scrutiny): 3
        - 80-99 (Imminent Detention): 4
        Supporting your cover with a valid item for this guard reduces the count by 1 (min 1).
        """
        susp = self.state.suspicion
        if susp >= 80:
            required = 4
        elif susp >= 40:
            required = 3
        elif susp >= 20:
            required = 2
        else:
            required = 1 if location_id == "museum_entrance" else 2

        if guard_id in self.state.guard_cover_supported:
            required = max(1, required - 1)
        return required

    def _evaluate_location_clearance(
        self,
        *,
        guard: GuardDef,
        substantive_turn: bool,
        had_contradiction: bool,
        convincing_explanation: bool = False,
    ) -> list[str]:
        """Determine whether the player's dialogue earned clearance for the active room.

        Required confirmations scale directly with suspicion tier. Only credible,
        non-ambiguous answers count — rambling/yapping never counts toward clearance.
        """
        if (
            had_contradiction
            or self.state.interrogation.active
            or self.state.interrogation_failed
        ):
            return []

        loc_id = self.state.current_location
        obj = self.routes.objective_for_location(loc_id)
        if obj is None or obj.id in self.state.completed_objectives:
            return []

        confirmations = self.state.guard_confirmations_count.get(guard.id, 0)
        required = self.required_confirmations_for(loc_id, guard.id)

        cleared = (substantive_turn and confirmations >= required) or convincing_explanation
        if not cleared:
            return []

        self.routes.complete_objective(self.state, obj.id)
        if guard.id not in self.state.cleared_guards:
            self.state.cleared_guards.append(guard.id)

        # Passing the security checkpoint issues a single-use curator Access Card
        granted_card = False
        if loc_id == "security_checkpoint" and self.state.inventory.get("access_card", 0) == 0:
            if "access_card" in self.scenario.items:
                self.inventory.grant_item(self.state, "access_card", 1)
                granted_card = True

        # Vault guard clearance unlocks the dedicated "Take the Gold Urn" action (no auto-skip!)
        if obj.id == "clear_vault_guard":
            self.state.last_notice = (
                "Vault security cleared! Click 'Take the Gold Urn' to grab the artifact."
            )
            self.state.auto_advance_to = None
            return [obj.id]

        # Final escape clearance finishes the heist
        if obj.id == "escape_with_urn":
            self.state.last_notice = "Exit cleared! You escaped the Grand Museum with the Gold Urn!"
            self.state.auto_advance_to = None
            return [obj.id]

        # Standard room clearance: schedule smooth auto-advance to the next location!
        next_route = next(
            (r for r in self.routes.available_routes(self.state) if r["is_forward"] and r["unlocked"]),
            None,
        )
        parts: list[str] = []
        if granted_card:
            parts.append("Acquired Access Card.")
        if next_route is not None:
            self.state.auto_advance_to = next_route["to_location"]
            parts.append(f"Cleared! Moving to {next_route['name']}...")
        if parts:
            self.state.last_notice = " ".join(parts)

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
        in_room = self.state.interrogation.in_room or self.state.interrogation.is_final
        return {
            "mission_summary": self.scenario.mission_briefing.get(
                "summary", self.scenario.summary
            ),
            "location": {
                "id": loc.id,
                "name": "Interrogation Room" if in_room else loc.name,
                "description": (
                    "A stark, windowless holding room beneath a harsh overhead lamp. Security logs cover the steel table."
                    if in_room
                    else loc.short_description
                ),
                "image": INTERROGATION_SCENE_IMAGE if in_room else (
                    VAULT_EMPTY_SCENE_IMAGE
                    if loc.id == "vault_display" and self.state.urn_taken
                    else loc.thumbnail
                ),
            },
            "scene": {
                "background": self.current_scene_image,
                "portrait": guard.portrait,
            },
            "objectives": self.routes.serialize_objectives(self.state),
            "dialogue": {
                "speaker": self.state.active_speaker or guard.name,
                "role": guard.role,
                "personality": "Interrogator Detective" if in_room else guard.personality.title(),
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
                "in_room": in_room,
                "is_final": self.state.interrogation.is_final,
                "status_label": (
                    "FINAL INTERROGATION"
                    if self.state.interrogation.is_final
                    else "INTERROGATION ROOM"
                    if in_room
                    else "DISCREPANCY CHECK"
                    if self.state.interrogation.pending_contradiction_id is not None
                    else None
                ),
                "evidence_quotes": list(self.state.interrogation.evidence_quotes),
                "discrepancy_summary": self.state.interrogation.discrepancy_summary,
            },
            "available_routes": self.routes.available_routes(self.state),
            "can_take_urn": self.can_take_urn,
            "urn_taken": self.state.urn_taken,
            "auto_advance_to": self.state.auto_advance_to,
            "can_voluntary_exit": self.endings.can_voluntary_exit(self.state),
            "prompt_injection_detected": self.state.prompt_injection_detected,
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
