"""Typed state and result models for the Bobbery Rob game engine."""

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ContradictionRecord:
    """An evidence-backed contradiction detected by the engine."""

    id: int
    slot: str
    earlier_claim_id: int
    earlier_value: str
    new_value: str
    reason: str
    evidence_turn_ids: list[int] = field(default_factory=list)
    evidence_quotes: list[str] = field(default_factory=list)
    guard_id: str = ""
    turn_id: int = 0
    resolved: bool = False
    resolution_evaluation: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContradictionRecord":
        return cls(
            id=data["id"],
            slot=data["slot"],
            earlier_claim_id=data["earlier_claim_id"],
            earlier_value=data["earlier_value"],
            new_value=data["new_value"],
            reason=data["reason"],
            evidence_turn_ids=list(data.get("evidence_turn_ids", [])),
            evidence_quotes=list(data.get("evidence_quotes", [])),
            guard_id=data.get("guard_id", ""),
            turn_id=data.get("turn_id", 0),
            resolved=bool(data.get("resolved", False)),
            resolution_evaluation=data.get("resolution_evaluation"),
        )


@dataclass
class InterrogationState:
    """Tracks active questioning, formal interrogation room, or final lockdown."""

    active: bool = False
    in_room: bool = False
    is_final: bool = False
    pending_contradiction_id: Optional[int] = None
    attempts_used: int = 0
    max_attempts: int = 2
    evidence_quotes: list[str] = field(default_factory=list)
    evidence_turn_ids: list[int] = field(default_factory=list)
    discrepancy_summary: str = ""
    blocks_clearance: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterrogationState":
        return cls(
            active=bool(data.get("active", False)),
            in_room=bool(data.get("in_room", False)),
            is_final=bool(data.get("is_final", False)),
            pending_contradiction_id=data.get("pending_contradiction_id"),
            attempts_used=int(data.get("attempts_used", 0)),
            max_attempts=int(data.get("max_attempts", 2)),
            evidence_quotes=list(data.get("evidence_quotes", [])),
            evidence_turn_ids=list(data.get("evidence_turn_ids", [])),
            discrepancy_summary=data.get("discrepancy_summary", ""),
            blocks_clearance=bool(data.get("blocks_clearance", False)),
        )


@dataclass
class PenaltyRecord:
    """A time penalty accrued during a mission run."""

    label: str
    seconds: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PenaltyRecord":
        return cls(label=data["label"], seconds=int(data["seconds"]))


@dataclass
class ItemUseResult:
    """Backend-validated result of attempting to use an inventory item."""

    item_id: str
    success: bool
    outcome: str  # "success" | "partial_success" | "failure" | "rejected"
    consumed: bool
    quantity_after: int
    suspicion_delta: int
    dialogue: str
    notice: str
    triggers_interrogation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MoveResult:
    """Backend-validated result of attempting to move between locations."""

    valid_route: bool
    transition_allowed: bool
    from_location: str
    target_location: str
    current_location_after: str
    notice: Optional[str] = None
    guard_opening_line: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TurnResult:
    """Structured outcome of processing one player dialogue turn."""

    status: str  # "ok" | "clarification_requested" | "contradiction_flagged" | "interrogation" | "ended" | "rejected"
    guard_id: str
    guard_name: str
    dialogue: str
    suspicion_before: int
    suspicion_after: int
    suspicion_delta: int
    suspicion_label: str
    notice: Optional[str] = None
    claims_recorded: list[dict[str, Any]] = field(default_factory=list)
    corrections_recorded: list[dict[str, Any]] = field(default_factory=list)
    contradictions_flagged: list[dict[str, Any]] = field(default_factory=list)
    explanation_evaluation: Optional[dict[str, Any]] = None
    item_result: Optional[dict[str, Any]] = None
    objectives_completed: list[str] = field(default_factory=list)
    auto_advance_to: Optional[str] = None
    interrogation_active: bool = False
    interrogation_is_final: bool = False
    ended: bool = False
    ending_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GameState:
    """Complete protected backend state for a single Bobbery Rob mission run."""

    scenario_id: str
    current_location: str
    suspicion: int
    inventory: dict[str, int]
    completed_objectives: list[str] = field(default_factory=list)
    visited_locations: list[str] = field(default_factory=list)
    cleared_guards: list[str] = field(default_factory=list)
    guard_cover_supported: list[str] = field(default_factory=list)
    items_used: list[str] = field(default_factory=list)
    items_presented_log: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[ContradictionRecord] = field(default_factory=list)
    interrogation: InterrogationState = field(default_factory=InterrogationState)
    interrogations_triggered: int = 0
    interrogation_failed: bool = False
    prompt_injection_detected: bool = False
    urn_taken: bool = False
    voluntary_exit: bool = False
    consecutive_evasions: int = 0
    guard_turns_count: dict[str, int] = field(default_factory=dict)
    guard_confirmations_count: dict[str, int] = field(default_factory=dict)
    active_speaker: str = ""
    active_dialogue: str = ""
    last_notice: Optional[str] = None
    auto_advance_to: Optional[str] = None
    interrogation_dismissal: bool = False
    authorization_route: Optional[str] = None  # "invitation" | "escort" | None
    security_story_verified: bool = False
    active_checks: dict[str, str] = field(default_factory=dict)
    penalties: list[PenaltyRecord] = field(default_factory=list)
    ended: bool = False
    ending_id: Optional[str] = None
    started_at: float = 0.0
    ended_at: Optional[float] = None
    player_id: Optional[str] = None
    codename: Optional[str] = None

    @property
    def unresolved_contradictions(self) -> list[ContradictionRecord]:
        return [c for c in self.contradictions if not c.resolved]

    @property
    def movement_locked(self) -> bool:
        return (
            self.ended
            or self.prompt_injection_detected
            or self.interrogation.active
            or self.suspicion >= 100
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "current_location": self.current_location,
            "suspicion": self.suspicion,
            "inventory": dict(self.inventory),
            "completed_objectives": list(self.completed_objectives),
            "visited_locations": list(self.visited_locations),
            "cleared_guards": list(self.cleared_guards),
            "guard_cover_supported": list(self.guard_cover_supported),
            "items_used": list(self.items_used),
            "items_presented_log": list(self.items_presented_log),
            "contradictions": [c.to_dict() for c in self.contradictions],
            "interrogation": self.interrogation.to_dict(),
            "interrogations_triggered": self.interrogations_triggered,
            "interrogation_failed": self.interrogation_failed,
            "prompt_injection_detected": self.prompt_injection_detected,
            "urn_taken": self.urn_taken,
            "voluntary_exit": self.voluntary_exit,
            "consecutive_evasions": self.consecutive_evasions,
            "guard_turns_count": dict(self.guard_turns_count),
            "guard_confirmations_count": dict(self.guard_confirmations_count),
            "active_speaker": self.active_speaker,
            "active_dialogue": self.active_dialogue,
            "last_notice": self.last_notice,
            "auto_advance_to": self.auto_advance_to,
            "interrogation_dismissal": self.interrogation_dismissal,
            "authorization_route": self.authorization_route,
            "security_story_verified": self.security_story_verified,
            "active_checks": dict(self.active_checks),
            "penalties": [p.to_dict() for p in self.penalties],
            "ended": self.ended,
            "ending_id": self.ending_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "player_id": self.player_id,
            "codename": self.codename,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        return cls(
            scenario_id=data["scenario_id"],
            current_location=data["current_location"],
            suspicion=int(data["suspicion"]),
            inventory={k: int(v) for k, v in data.get("inventory", {}).items()},
            completed_objectives=list(data.get("completed_objectives", [])),
            visited_locations=list(data.get("visited_locations", [])),
            cleared_guards=list(data.get("cleared_guards", [])),
            guard_cover_supported=list(data.get("guard_cover_supported", [])),
            items_used=list(data.get("items_used", [])),
            items_presented_log=list(data.get("items_presented_log", [])),
            contradictions=[
                ContradictionRecord.from_dict(c) for c in data.get("contradictions", [])
            ],
            interrogation=InterrogationState.from_dict(data.get("interrogation", {})),
            interrogations_triggered=int(data.get("interrogations_triggered", 0)),
            interrogation_failed=bool(data.get("interrogation_failed", False)),
            prompt_injection_detected=bool(data.get("prompt_injection_detected", False)),
            urn_taken=bool(data.get("urn_taken", False)),
            voluntary_exit=bool(data.get("voluntary_exit", False)),
            consecutive_evasions=int(data.get("consecutive_evasions", 0)),
            guard_turns_count={
                k: int(v) for k, v in data.get("guard_turns_count", {}).items()
            },
            guard_confirmations_count={
                k: int(v) for k, v in data.get("guard_confirmations_count", {}).items()
            },
            active_speaker=data.get("active_speaker", ""),
            active_dialogue=data.get("active_dialogue", ""),
            last_notice=data.get("last_notice"),
            auto_advance_to=data.get("auto_advance_to"),
            interrogation_dismissal=bool(data.get("interrogation_dismissal", False)),
            authorization_route=data.get("authorization_route"),
            security_story_verified=bool(data.get("security_story_verified", False)),
            active_checks={str(k): str(v) for k, v in data.get("active_checks", {}).items()},
            penalties=[PenaltyRecord.from_dict(p) for p in data.get("penalties", [])],
            ended=bool(data.get("ended", False)),
            ending_id=data.get("ending_id"),
            started_at=float(data.get("started_at", 0.0)),
            ended_at=data.get("ended_at"),
            player_id=data.get("player_id"),
            codename=data.get("codename"),
        )
