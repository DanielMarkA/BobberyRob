"""Conversation archive for Bobbery Rob.

Maintains an append-only sequence of conversation turns.
"""

from typing import Any

from memory.models import SPEAKERS, Turn


class Archive:
    """Append-only store for dialogue turns."""

    def __init__(self, turns: list[Turn] | None = None) -> None:
        self._turns: list[Turn] = []
        self._turns_by_id: dict[int, Turn] = {}
        if turns:
            for turn in turns:
                self._turns.append(turn)
                self._turns_by_id[turn.turn_id] = turn

    def add_turn(
        self,
        speaker: str,
        text: str,
        guard_id: str | None = None,
        location_id: str | None = None,
    ) -> Turn:
        """Add a new turn to the archive with a sequential turn_id starting at 1."""
        if speaker not in SPEAKERS:
            raise ValueError(f"Invalid speaker '{speaker}'. Must be one of: {', '.join(SPEAKERS)}")

        next_id = max(self._turns_by_id.keys(), default=0) + 1
        turn = Turn(
            turn_id=next_id,
            speaker=speaker,
            text=text,
            guard_id=guard_id,
            location_id=location_id,
        )
        self._turns.append(turn)
        self._turns_by_id[turn.turn_id] = turn
        return turn

    def get_turn(self, turn_id: int) -> Turn:
        """Retrieve a turn by turn_id. Raises KeyError if not found."""
        if turn_id not in self._turns_by_id:
            raise KeyError(f"Turn with turn_id {turn_id} does not exist.")
        return self._turns_by_id[turn_id]

    def has_turn(self, turn_id: int) -> bool:
        """Check if a turn exists in the archive."""
        return turn_id in self._turns_by_id

    def recent_turns(self, n: int) -> list[Turn]:
        """Return the last n turns in chronological order."""
        if n <= 0:
            return []
        return list(self._turns[-n:])

    def turns_for_guard(self, guard_id: str) -> list[Turn]:
        """Return all turns where the specified guard was present."""
        return [t for t in self._turns if t.guard_id == guard_id]

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialize all turns to plain dictionaries."""
        return [t.to_dict() for t in self._turns]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> "Archive":
        """Deserialize archive from a list of turn dictionaries."""
        turns = [Turn.from_dict(item) for item in data]
        return cls(turns=turns)
