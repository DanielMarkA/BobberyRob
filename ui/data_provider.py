"""Temporary data for the frontend.

PHASE 6: replace the bodies of these functions with real backend calls.
Keep the return shapes the same so no UI code has to change.
"""

import re
import copy
import time

import streamlit as st # mock only: remove when the real backend replaces the mocks

RUN_CATEGORIES = ["Perfect Run", "Successful Run", "Compromised Run", "Alternative Run"]

_MOCK_PERFECT = [
    ("Phantom", 134), ("Shadow", 148), ("Ghost", 161), ("Cipher", 177),
    ("Unknown", 192), ("Nexus", 206), ("Raven", 219), ("Atlas", 234),
    ("Vector", 248), ("Zenith", 263),
]

_MOCK_REPLIES = [
    ("Interesting. And who invited you?", 38, "Moderate Attention"),
    ("May I see some identification?", 42, "Moderate Attention"),
    ("Hmm. Wait here a moment, please.", 55, "Increased Scrutiny"),
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

def enter_game(codename: str) -> dict:
    """Validate and register a codename.

    Returns: {"ok": bool, "player_id": str | None, "error": str | None}
    PHASE 6: replace with the real backend call. The rules below are
    PROPOSALS for testing the UI, and the backend team owns the final rules.
    """
    name = codename.strip()

    if not name:
        return _fail("Enter a codename to continue.")
    if not 3 <= len(name) <= 16:
        return _fail("Codename must be 3–16 characters.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        return _fail("Use letters, numbers, hyphens and underscores only.")
    if name.lower() in {n.lower() for n, _ in _MOCK_PERFECT}:
        return _fail("That codename is already taken.")

    return {"ok": True, "player_id": f"mock-{name.lower()}", "error": None}

def get_mission_briefing() -> dict:
    """Return the mission configuration shown on the briefing screen.

    PHASE 6: replace with the real call (data comes from scenarios/museum.json).
    "location_image" is None until artwork exists.
    """
    return {
        "title": "The Forgotten Artifact",
        "summary": (
            "A priceless artifact has reportedly gone missing from the museum's "
            "restricted collection. Your task is to reach the restricted area "
            "and uncover what really happened."
        ),
        "location_name": "The National Museum",
        "location_image": None,
        "primary_objective": "Gain access to the Restricted Collection Area.",
        "optional_objectives": [
            "Discover the truth about the missing artifact.",
            "Avoid raising suspicion.",
        ],
        "information": (
            "The museum is under heightened security due to the incident. "
            "Guards will be more alert than usual."
        ),
    }

def start_mission() -> dict:
    """Tell the backend the player pressed Start Mission (this starts the timer).

    Returns: {"ok": bool, "error": str | None}
    PHASE 6: the backend creates the run and starts the clock here.
    """
    return {"ok": True, "error": None}

def get_game_state() -> dict:
    """Return the full current game state for the gameplay screen.

    PHASE 6: replace with the real backend call. After every player action the
    backend returns this same shape, and the UI just redraws from it.
    The frontend never calculates suspicion, objectives or inventory itself.
    """
    st.session_state["_mock_turn"] = 0

    return {
        "mission_summary": (
            "A rare artifact is being moved into a restricted collection area. "
            "Your objective is to reach the restricted area and retrieve the artifact."
        ),
        "location": {"name": "Main Exhibition Hall", "image": None},
        "objectives": [
            {"text": "Enter the Museum", "done": True},
            {"text": "Reach the Main Hall", "done": False},
            {"text": "Pass the Security Checkpoint", "done": False},
            {"text": "Reach the Restricted Area", "done": False},
            {"text": "Retrieve the Artifact", "done": False},
        ],
        "dialogue": {
            "speaker": "Security Guard",
            "text": "Good evening. What brings you to the museum?",
        },
        "suspicion": {"value": 35, "label": "Moderate Attention"},
        "inventory": [
            {"id": "fake_passport", "name": "Fake Passport", "quantity": 1, "icon": "PASS"},
            {"id": "bribe_money", "name": "Bribe Money", "quantity": 3, "icon": "CASH"},
            {"id": "invitation_letter", "name": "Invitation Letter", "quantity": 1, "icon": "LETTER"},
        ],
        "notice": "Maintain your composure. Inconsistent statements may raise suspicion.",
    }

def submit_response(text: str) -> dict:
    """Send the player's response to the backend and return the NEW full game state.

    Same shape as get_game_state(). PHASE 6: replace this with the real call.
    The backend sends the text to the AI, validates the result, updates state.
    (This mock reads session_state only because it has no server. The real
    backend keeps the game state itself.)
    """
    time.sleep(1.2)  # simulate AI latency so the spinner is visible
    if text.strip().lower() == "/fail":  # test hook for the error path
        raise RuntimeError("simulated backend failure")

    game = copy.deepcopy(st.session_state["game"])
    turn = st.session_state.get("_mock_turn", 0)
    reply, value, label = _MOCK_REPLIES[turn % len(_MOCK_REPLIES)]
    st.session_state["_mock_turn"] = turn + 1

    game["dialogue"]["text"] = reply
    game["suspicion"] = {"value": value, "label": label}
    return game

def _fail(message: str) -> dict:
    return {"ok": False, "player_id": None, "error": message}