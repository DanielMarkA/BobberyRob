"""Temporary data for the frontend.

PHASE 6: replace the bodies of these functions with real backend calls.
Keep the return shapes the same so no UI code has to change.
"""

RUN_CATEGORIES = ["Perfect Run", "Successful Run", "Compromised Run", "Alternative Run"]

_MOCK_PERFECT = [
    ("Phantom", 134), ("Shadow", 148), ("Ghost", 161), ("Cipher", 177),
    ("Unknown", 192), ("Nexus", 206), ("Raven", 219), ("Atlas", 234),
    ("Vector", 248), ("Zenith", 263),
]


def get_leaderboard(category: str) -> list[dict]:
    """Return ranked entries for one run category.

    Each entry: {"rank": int, "player": str, "time_seconds": int}
    time_seconds is the ADJUSTED completion time, calculated by the backend.
    """
    if category == "Perfect Run":
        rows = _MOCK_PERFECT
    elif category == "Successful Run":
        rows = [(name, secs + 40) for name, secs in _MOCK_PERFECT[:7]]
    elif category == "Compromised Run":
        rows = [(name, secs + 95) for name, secs in _MOCK_PERFECT[:3]]
    else:
        rows = []  # Alternative Run: empty on purpose, to test the empty state

    return [
        {"rank": i, "player": name, "time_seconds": secs}
        for i, (name, secs) in enumerate(rows, start=1)
    ]