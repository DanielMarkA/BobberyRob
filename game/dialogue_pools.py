"""Curated dialogue variation pools for openings, item reactions, and neutral fallbacks.

Rules never change across replays — only the phrasing varies.
"""

import random
from typing import Optional

GUARD_OPENINGS: dict[str, tuple[str, ...]] = {
    "guard_casual": (
        "Hey there! Welcome to the Grand Museum—just need your name and what brings you in tonight.",
        "Evening! Quiet shift tonight. Mind signing in with your name and reason for visiting?",
        "Welcome to the Grand Museum. Before you head inside, who should I put down on the log and what brings you here?",
    ),
    "guard_strict": (
        "Halt. The main gallery is under strict perimeter surveillance tonight. State your credentials.",
        "Hold right there. The exhibition wing is closed to the public—identify yourself and your affiliation.",
        "Stop. No one crosses the Main Exhibition Hall after hours without verification. State your business.",
    ),
    "guard_observant": (
        "Step forward to the scanner, please. Explain why you need restricted access and present your authorization.",
        "Security checkpoint. State why your visit requires entry to the restricted wing, and show your clearance.",
        "Hold at the line. Restricted access requires both a valid reason and verifiable authorization—let's hear it.",
    ),
    "guard_experienced": (
        "Thirty years here, and I know every curator on staff. Confirm your clearance for the restricted archives.",
        "This wing is archives-only. Confirm the authorization that got you past the checkpoint.",
        "You're a long way from the gala floor. Confirm your clearance and who signed off on your access.",
    ),
    "guard_impatient": (
        "Make it quick, we're locking down the vault in five minutes. Confirm your clearance for the sanctum.",
        "Five minutes till auto-lock. Confirm your vault authorization and state your business—fast.",
        "Vault lockdown is imminent. Confirm your clearance right now or step back into the corridor.",
    ),
    "guard_exit": (
        "Hold on—before I unlock the exit doors, what's in that satchel and how does it fit your visit tonight?",
        "Not so fast. Every after-hours departure gets logged—account for what you're carrying out of here.",
        "Stop at the doors. Explain what you're taking out of the museum tonight before I release the lock.",
    ),
}

ITEM_REACTIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("fake_passport", "guard_casual"): (
        "Let me take a look... Everything looks in order. Welcome, Doctor.",
        "Academic visas and all—looks solid to me. Go right ahead.",
    ),
    ("invitation_letter", "guard_observant"): (
        "Presidential seal verified. Your invitation authorizes restricted wing access—now explain why your visit requires it.",
        "Board President's signature checks out. That covers your authorization; tell me why you need into the restricted collection.",
    ),
    ("invitation_letter", "guard_casual"): (
        "An executive gala invitation! Always a pleasure—go right on in.",
        "Signed by the Board President himself! Welcome to the evening, esteemed guest.",
    ),
    ("access_card", "guard_experienced"): (
        "Senior curator keycard checks out. Keep your hands off the preservation seals.",
        "Level-4 card reads clean on the terminal. Watch your step around the archival cases.",
    ),
    ("access_card", "guard_impatient"): (
        "Card accepted. You've got less than five minutes before auto-lock.",
        "Keycard cleared. Hurry up—this vault seals itself in minutes.",
    ),
}

NEUTRAL_FALLBACKS: tuple[str, ...] = (
    "Hold on a moment—radio static cut you off. Say that again?",
    "Sorry, didn't catch that over the security channel. Repeat what you just said.",
    "One second, my earpiece buzzed out. Tell me that again clearly.",
)


def pick_opening(guard_id: str, default: str, rng: Optional[random.Random] = None) -> str:
    pool = GUARD_OPENINGS.get(guard_id)
    if not pool:
        return default
    chooser = rng if rng is not None else random
    return chooser.choice(pool)


def pick_item_reaction(
    item_id: str,
    guard_id: str,
    default: str,
    rng: Optional[random.Random] = None,
) -> str:
    pool = ITEM_REACTIONS.get((item_id, guard_id))
    if not pool:
        return default
    chooser = rng if rng is not None else random
    return chooser.choice(pool)


def pick_neutral_fallback(rng: Optional[random.Random] = None) -> str:
    chooser = rng if rng is not None else random
    return chooser.choice(NEUTRAL_FALLBACKS)
