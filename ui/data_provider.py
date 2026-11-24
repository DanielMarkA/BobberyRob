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

_MOCK_ITEM_OUTCOMES = {
    # item_id: (guard dialogue, notice, is the item consumed?)
    "fake_passport": ("Let me take a look... This seems to be in order.", "Passport inspected.", False),
    "bribe_money": ("Hm. I didn't see anything. Move along.", "The guard pockets the money and looks away.", True),
    "invitation_letter": ("An invitation. Who signed it?", "The guard is reading your letter closely.", False),
}

_MOCK_RESULTS = {
    "success": {
        "heading": "MISSION COMPLETE",
        "outcome_label": "Successful Infiltration",
        "tone": "success",  # success | partial | failure (styling only)
        "raw_seconds": 512.36,
        "penalties": [{"label": "Failed Access Penalty", "seconds": 30}],
        "adjusted_seconds": 542.36,
        "final_suspicion": 24,
        "objectives_done": 3,
        "objectives_total": 3,
        "personal_best_seconds": 542.36,
        "is_new_record": True,
        "quote": "Another successful operation, Rob.",
        "quote_by": "The Agency",
        "scene_caption": "Grand Museum interior",
    },
    "compromised": {
        "heading": "MISSION COMPLETE",
        "outcome_label": "Compromised Victory",
        "tone": "partial",
        "raw_seconds": 611.5,
        "penalties": [
            {"label": "Failed Access Penalty", "seconds": 30},
            {"label": "Unconvincing Explanation Penalty", "seconds": 60},
        ],
        "adjusted_seconds": 701.5,
        "final_suspicion": 78,
        "objectives_done": 2,
        "objectives_total": 3,
        "personal_best_seconds": 542.36,
        "is_new_record": False,
        "quote": "You got out. Barely.",
        "quote_by": "The Agency",
        "scene_caption": "Museum exit",
    },
    "captured": {
        "heading": "MISSION FAILED",
        "outcome_label": "Captured",
        "tone": "failure",
        "raw_seconds": 305.2,
        "penalties": [],
        "adjusted_seconds": None,  # failed attempts are not ranked
        "final_suspicion": 100,
        "objectives_done": 1,
        "objectives_total": 3,
        "personal_best_seconds": 542.36,
        "is_new_record": False,
        "quote": "The Agency does not know you.",
        "quote_by": "The Agency",
        "scene_caption": "Holding room",
    },
}

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
    "location_image" can be None when a scenario has no artwork.
    """
    return {
        "title": "The Forgotten Artifact",
        "summary": "A priceless artifact has vanished from the museum's restricted collection.",
        "location_name": "Grand Museum",
        "location_image": "/app/static/images/museum_entrance.webp",
        "primary_objective": "Enter the restricted collection.",
        "optional_objectives": [
            "Discover what happened.",
            "Keep suspicion low.",
        ],
        "information": "Guards are on high alert.",
    }

def start_mission() -> dict:
    """Tell the backend the player pressed Start Mission (this starts the timer).

    Returns: {"ok": bool, "error": str | None}
    PHASE 6: the backend creates the run and starts the clock here.
    """
    st.session_state["_mock_mission_started_at"] = time.monotonic()
    return {"ok": True, "error": None}


def get_mission_elapsed_seconds() -> int:
    """Return the running mission's elapsed time, without rerunning the game."""
    now = time.monotonic()
    started_at = st.session_state.setdefault("_mock_mission_started_at", now)
    return max(0, int(now - started_at))


def get_game_state() -> dict:
    """Return the full current game state for the gameplay screen.

    PHASE 6: replace with the real backend call. After every player action the
    backend returns this same shape, and the UI just redraws from it.
    The frontend never calculates suspicion, objectives or inventory itself.
    """
    st.session_state["_mock_turn"] = 0

    return {
        "mission_summary": (
            "An artifact has vanished from the restricted collection. Find out what happened."
        ),
        "location": {
            "name": "Main Exhibition Hall",
            "image": "/app/static/images/main_exhibition_hall_thumb.webp",
        },
        "scene": {
            "background": "/app/static/images/main_exhibition_hall.webp",
            "portrait": "/app/static/images/casual.webp",
        },
        "objectives": [
            {"text": "Enter the museum", "done": True},
            {"text": "Reach the main hall", "done": False},
            {"text": "Pass security", "done": False},
            {"text": "Enter the restricted area", "done": False},
            {"text": "Investigate the artifact", "done": False},
        ],
        "dialogue": {
            "speaker": "Security Guard",
            "text": "Good evening. What brings you to the museum?",
        },
        "suspicion": {"value": 35, "label": "Moderate Attention"},
        "inventory": [
            {"id": "fake_passport", "name": "Fake Passport", "quantity": 1,
             "image": "/app/static/inventory/fake_passport.png"},
            {"id": "bribe_money", "name": "Bribe Money", "quantity": 3,
             "image": "/app/static/inventory/bribe_money.png"},
            {"id": "invitation_letter", "name": "Invitation Letter", "quantity": 1,
             "image": "/app/static/inventory/invitation_letter.png"},
        ],
        "notice": None,
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
    game["notice"] = None
    return game

def use_item(item_id: str) -> dict:
    """Ask the backend to use an item. Returns the NEW full game state.

    PHASE 6: replace with the real call. The backend validates ownership,
    quantity and usage conditions, and reports problems via state["notice"].
    """
    time.sleep(0.8)  # simulate latency
    game = copy.deepcopy(st.session_state["game"])

    item = next((i for i in game["inventory"] if i["id"] == item_id), None)
    if item is None or item["quantity"] <= 0:
        game["notice"] = "You don't have that item."
        return game

    dialogue, notice, consumed = _MOCK_ITEM_OUTCOMES.get(
        item_id, ("...", "Item used.", False)
    )
    if consumed:
        item["quantity"] -= 1
    game["dialogue"]["text"] = dialogue
    game["notice"] = notice
    return game

def get_mission_result() -> dict:
    """Return the finished mission's results.

    PHASE 6: replace with the real call. Every number here is calculated by the
    backend; the UI only formats and displays them. adjusted_seconds and
    personal_best_seconds may be None.
    """
    ending = st.session_state.get("_mock_ending", "success")  # mock only
    return copy.deepcopy(_MOCK_RESULTS[ending])

def _fail(message: str) -> dict:
    return {"ok": False, "player_id": None, "error": message}
