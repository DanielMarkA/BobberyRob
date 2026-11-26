"""Data models and constants for the Bobbery Rob memory system."""

from dataclasses import asdict, dataclass, field
from typing import Any

SPEAKERS: tuple[str, ...] = ("player", "guard")

SLOTS: tuple[str, ...] = (
    "name",
    "occupation",
    "employer",
    "hometown",
    "reason_for_visit",
    "relationships",
    "other",
)

STATUSES: tuple[str, ...] = (
    "asserted",
    "ambiguous",
    "corrected",
    "disputed",
)


@dataclass
class Turn:
    """A single dialogue turn in the conversation archive."""

    turn_id: int
    speaker: str
    text: str
    guard_id: str | None = None
    location_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            turn_id=data["turn_id"],
            speaker=data["speaker"],
            text=data["text"],
            guard_id=data.get("guard_id"),
            location_id=data.get("location_id"),
        )


@dataclass
class Claim:
    """A structured assertion made during a turn."""

    id: int
    slot: str
    value: str
    source_turn: int
    status: str = "asserted"
    supersedes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        return cls(
            id=data["id"],
            slot=data["slot"],
            value=data["value"],
            source_turn=data["source_turn"],
            status=data.get("status", "asserted"),
            supersedes=data.get("supersedes"),
        )


@dataclass
class Report:
    """A security report shared among guards."""

    report_id: int
    source_turn: int
    summary: str
    shared_with: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Report":
        return cls(
            report_id=data["report_id"],
            source_turn=data["source_turn"],
            summary=data["summary"],
            shared_with=list(data.get("shared_with", [])),
        )
