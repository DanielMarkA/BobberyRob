"""Retrieval helpers for candidate conflicts and original source evidence."""

from collections.abc import Iterable

from memory.archive import Archive
from memory.claims import ClaimStore
from memory.models import Claim, Turn


def find_candidates_for(claim_id: int, claim_store: ClaimStore) -> list[Claim]:
    """Return earlier claims in the same slot, including superseded ones.

    Returns an empty list if there are no earlier claims in that slot.
    """
    target = claim_store.get_claim(claim_id)
    return [c for c in claim_store.all_claims() if c.slot == target.slot and c.id < target.id]


def find_evidence(
    claim_ids: Iterable[int],
    claim_store: ClaimStore,
    archive: Archive,
) -> list[Turn]:
    """Return the exact original source turns for given claim IDs without duplicates."""
    source_turn_ids: list[int] = []
    seen_turns: set[int] = set()

    for cid in claim_ids:
        claim = claim_store.get_claim(cid)
        if claim.source_turn not in seen_turns:
            seen_turns.add(claim.source_turn)
            source_turn_ids.append(claim.source_turn)

    # Return original turns in the order they were referenced
    return [archive.get_turn(tid) for tid in source_turn_ids]
