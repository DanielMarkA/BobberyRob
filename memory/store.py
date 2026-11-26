"""Unified MemoryStore API for Bobbery Rob.

Provides a single entry point for storing dialogue turns, claims, security
reports, and performing retrieval for contradiction checks.
"""

from collections.abc import Iterable
from typing import Any

from memory.archive import Archive
from memory.claims import ClaimStore
from memory.guard_memory import GuardMemory
from memory.models import (
    Claim,
    Report,
    Turn,
)
from memory.retrieval import find_candidates_for, find_evidence


class MemoryStore:
    """The central memory store for Bobbery Rob.

    Encapsulates dialogue archives, claim tracking, guard visibility, and
    evidence retrieval.
    """

    def __init__(
        self,
        archive: Archive | None = None,
        claims: ClaimStore | None = None,
        guard_memory: GuardMemory | None = None,
    ) -> None:
        self._archive = archive if archive is not None else Archive()
        self._claims = claims if claims is not None else ClaimStore()
        self._guard_memory = guard_memory if guard_memory is not None else GuardMemory()

    # -------------------------------------------------------------------------
    # Archive methods
    # -------------------------------------------------------------------------

    def add_turn(
        self,
        speaker: str,
        text: str,
        guard_id: str | None = None,
        location_id: str | None = None,
    ) -> Turn:
        """Add a turn to the conversation archive.

        Args:
            speaker: 'player' or 'guard'.
            text: Dialogue text spoken.
            guard_id: Optional ID of the guard present.
            location_id: Optional ID of the current location.

        Returns:
            The created Turn instance with sequential turn_id.
        """
        return self._archive.add_turn(
            speaker=speaker,
            text=text,
            guard_id=guard_id,
            location_id=location_id,
        )

    def get_turn(self, turn_id: int) -> Turn:
        """Get a turn by ID. Raises KeyError if missing."""
        return self._archive.get_turn(turn_id)

    def recent_turns(self, n: int) -> list[Turn]:
        """Return the last n turns in chronological order."""
        return self._archive.recent_turns(n)

    def turns_for_guard(self, guard_id: str) -> list[Turn]:
        """Return all turns where the specified guard was present."""
        return self._archive.turns_for_guard(guard_id)

    # -------------------------------------------------------------------------
    # Claims methods
    # -------------------------------------------------------------------------

    def add_claim(
        self,
        slot: str,
        value: str,
        source_turn: int,
        status: str = "asserted",
    ) -> Claim:
        """Record a structured claim.

        Validates that:
        - slot is in SLOTS
        - status is in STATUSES
        - source_turn exists in the archive

        Returns:
            The created Claim instance with sequential id.
        """
        return self._claims.add_claim(
            slot=slot,
            value=value,
            source_turn=source_turn,
            status=status,
            turn_validator=self._archive.has_turn,
        )

    def get_claim(self, claim_id: int) -> Claim:
        """Get a claim by its ID. Raises KeyError if missing."""
        return self._claims.get_claim(claim_id)

    def correct_claim(
        self,
        old_claim_id: int,
        new_value: str,
        source_turn: int,
    ) -> Claim:
        """Correct an existing claim.

        Marks the old claim's status as 'corrected', and creates a new claim
        pointing to the old one via `supersedes`.
        """
        return self._claims.correct_claim(
            old_claim_id=old_claim_id,
            new_value=new_value,
            source_turn=source_turn,
            turn_validator=self._archive.has_turn,
        )

    def set_status(self, claim_id: int, status: str) -> None:
        """Update an existing claim's status ('asserted', 'ambiguous', 'corrected', 'disputed')."""
        self._claims.set_status(claim_id, status)

    def claims_in_slot(self, slot: str) -> list[Claim]:
        """Return all claims recorded for the given slot."""
        return self._claims.claims_in_slot(slot)

    # -------------------------------------------------------------------------
    # Retrieval methods
    # -------------------------------------------------------------------------

    def candidates_for(self, claim_id: int) -> list[Claim]:
        """Return earlier claims in the same slot, including superseded ones.

        Missing information is not a contradiction: returns an empty list if
        no earlier claims exist for this slot.
        """
        return find_candidates_for(claim_id, self._claims)

    def evidence(self, claim_ids: Iterable[int]) -> list[Turn]:
        """Return original source turns for given claim IDs without duplicates or rewording."""
        return find_evidence(claim_ids, self._claims, self._archive)

    # -------------------------------------------------------------------------
    # Guard memory and shared reports
    # -------------------------------------------------------------------------

    def add_report(
        self,
        source_turn: int,
        summary: str,
        shared_with: list[str] | None = None,
    ) -> Report:
        """Add a shared security report referencing a source turn.

        Args:
            source_turn: Turn ID where the event occurred.
            summary: Human/AI-provided summary of the event.
            shared_with: List of guard IDs who receive the report. Empty list means all guards.
        """
        return self._guard_memory.add_report(
            source_turn=source_turn,
            summary=summary,
            shared_with=shared_with,
            turn_validator=self._archive.has_turn,
        )

    def guard_view(self, guard_id: str) -> dict[str, Any]:
        """Return the memory perspective for a specific guard.

        Returns a dictionary containing:
        - 'turns': turns this guard witnessed
        - 'claims': claims made during those turns
        - 'reports': security reports shared with this guard (or with all guards)
        """
        return self._guard_memory.guard_view(
            guard_id=guard_id,
            archive=self._archive,
            claim_store=self._claims,
        )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize complete memory state into plain dicts/lists."""
        return {
            "turns": self._archive.to_dict(),
            "claims": self._claims.to_dict(),
            "reports": self._guard_memory.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryStore":
        """Deserialize MemoryStore from plain dict."""
        archive = Archive.from_dict(data.get("turns", []))
        claims = ClaimStore.from_dict(data.get("claims", []))
        guard_memory = GuardMemory.from_dict(data.get("reports", []))
        return cls(archive=archive, claims=claims, guard_memory=guard_memory)
