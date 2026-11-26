"""Claim store for Bobbery Rob.

Maintains structured claims made during the game, including revisions and status.
"""

from collections.abc import Callable
from typing import Any

from memory.models import SLOTS, STATUSES, Claim


class ClaimStore:
    """Store for game claims, corrections, and slot queries."""

    def __init__(self, claims: list[Claim] | None = None) -> None:
        self._claims: list[Claim] = []
        self._claims_by_id: dict[int, Claim] = {}
        if claims:
            for claim in claims:
                self._claims.append(claim)
                self._claims_by_id[claim.id] = claim

    def add_claim(
        self,
        slot: str,
        value: str,
        source_turn: int,
        status: str = "asserted",
        supersedes: int | None = None,
        turn_validator: Callable[[int], bool] | None = None,
    ) -> Claim:
        """Add a new claim with validation."""
        if slot not in SLOTS:
            raise ValueError(f"Invalid slot '{slot}'. Must be one of: {', '.join(SLOTS)}")

        if status not in STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(STATUSES)}")

        if turn_validator is not None and not turn_validator(source_turn):
            raise ValueError(
                f"Source turn {source_turn} does not exist in the conversation archive."
            )

        if supersedes is not None and supersedes not in self._claims_by_id:
            raise KeyError(f"Superseded claim with id {supersedes} does not exist.")

        next_id = max(self._claims_by_id.keys(), default=0) + 1
        claim = Claim(
            id=next_id,
            slot=slot,
            value=value,
            source_turn=source_turn,
            status=status,
            supersedes=supersedes,
        )
        self._claims.append(claim)
        self._claims_by_id[claim.id] = claim
        return claim

    def get_claim(self, claim_id: int) -> Claim:
        """Retrieve a claim by its ID. Raises KeyError if not found."""
        if claim_id not in self._claims_by_id:
            raise KeyError(f"Claim with id {claim_id} does not exist.")
        return self._claims_by_id[claim_id]

    def correct_claim(
        self,
        old_claim_id: int,
        new_value: str,
        source_turn: int,
        turn_validator: Callable[[int], bool] | None = None,
    ) -> Claim:
        """Correct an earlier claim.

        Appends a new claim with `supersedes` set to `old_claim_id`, and marks
        the old claim's status as 'corrected'.
        """
        old_claim = self.get_claim(old_claim_id)

        if turn_validator is not None and not turn_validator(source_turn):
            raise ValueError(
                f"Source turn {source_turn} does not exist in the conversation archive."
            )

        old_claim.status = "corrected"
        return self.add_claim(
            slot=old_claim.slot,
            value=new_value,
            source_turn=source_turn,
            status="asserted",
            supersedes=old_claim_id,
            turn_validator=turn_validator,
        )

    def set_status(self, claim_id: int, status: str) -> None:
        """Update the status of an existing claim."""
        if status not in STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(STATUSES)}")
        claim = self.get_claim(claim_id)
        claim.status = status

    def claims_in_slot(self, slot: str) -> list[Claim]:
        """Return all claims in the specified slot."""
        if slot not in SLOTS:
            raise ValueError(f"Invalid slot '{slot}'. Must be one of: {', '.join(SLOTS)}")
        return [c for c in self._claims if c.slot == slot]

    def all_claims(self) -> list[Claim]:
        """Return a copy of all claims."""
        return list(self._claims)

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialize all claims to plain dictionaries."""
        return [c.to_dict() for c in self._claims]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> "ClaimStore":
        """Deserialize claim store from a list of claim dictionaries."""
        claims = [Claim.from_dict(item) for item in data]
        return cls(claims=claims)
