"""Backend bridge for the Streamlit frontend.

Connects UI screens and components to `GameEngine`, `ScenarioConfig`, and
`GameDatabase` while keeping the UI return shapes stable.
"""

import logging
from typing import Any, Optional

import streamlit as st

from database import GameDatabase
from game import GameEngine
from llm import MockLLMClient, get_client
from scenario.loader import ScenarioConfig, load_scenario

log = logging.getLogger(__name__)

RUN_CATEGORIES = ["Perfect Run", "Successful Run", "Compromised Run", "Alternative Run"]

_DEV_ENDING_MAP = {
    "success": "successful_infiltration",
    "compromised": "compromised_victory",
    "captured": "capture_failure",
    "perfect": "perfect_infiltration",
    "alternate": "alternate_ending",
}


def _get_db() -> GameDatabase:
    if "_db" not in st.session_state:
        st.session_state["_db"] = GameDatabase()
    return st.session_state["_db"]


def _get_scenario() -> ScenarioConfig:
    if "_scenario" not in st.session_state:
        st.session_state["_scenario"] = load_scenario()
    return st.session_state["_scenario"]


def _create_llm_client() -> tuple[Any, bool]:
    """Return `(client, used_offline_fallback)`."""
    try:
        client = get_client()
        return client, isinstance(client, MockLLMClient)
    except RuntimeError as exc:
        log.warning("Falling back to MockLLMClient: %s", exc)
        return MockLLMClient(), True


def _get_or_create_engine() -> GameEngine:
    if "_engine" not in st.session_state:
        start_mission()
    return st.session_state["_engine"]


def _persist_if_ended(engine: GameEngine) -> None:
    """Persist a completed run once and cache its debrief payload."""
    if not engine.state.ended or st.session_state.get("_saved_run_result") is not None:
        return

    ending = (
        engine.scenario.endings.get(engine.state.ending_id)
        if engine.state.ending_id
        else engine.endings.evaluate(engine.state)
    )
    if ending is None:
        return

    raw_payload = engine.get_result()
    player = st.session_state.get("player") or {}
    player_id = player.get("player_id") or engine.state.player_id or "guest"
    codename = player.get("codename") or engine.state.codename or "Agent"

    db_record = _get_db().record_run(
        player_id=player_id,
        codename=codename,
        scenario_id=engine.scenario.scenario_id,
        ending_id=ending.id,
        category=raw_payload["category"],
        raw_seconds=raw_payload["raw_seconds"],
        adjusted_seconds=raw_payload["adjusted_seconds"],
        final_suspicion=raw_payload["final_suspicion"],
        objectives_done=raw_payload["objectives_done"],
        objectives_total=raw_payload["objectives_total"],
    )

    st.session_state["_saved_run_result"] = engine.get_result(
        personal_best_seconds=db_record["personal_best_seconds"],
        is_new_record=db_record["is_new_record"],
    )


def get_leaderboard(category: str) -> list[dict]:
    """Return ranked entries for one run category from SQLite."""
    return _get_db().get_leaderboard(category)


def enter_game(codename: str) -> dict:
    """Validate and register (or look up) a player codename in SQLite."""
    return _get_db().register_or_get_player(codename)


def get_mission_briefing() -> dict:
    """Return the mission briefing configuration from scenario/museum.json."""
    scenario = _get_scenario()
    briefing = dict(scenario.mission_briefing)
    # Use the polished briefing target photo if the scenario still points to entrance
    briefing.setdefault("title", scenario.title)
    briefing.setdefault("summary", scenario.summary)
    briefing.setdefault("location_name", scenario.location_name)
    briefing.setdefault("location_image", scenario.location_image)
    return briefing


def start_mission() -> dict:
    """Create a fresh GameEngine run and start the mission timer."""
    scenario = _get_scenario()
    client, is_mock = _create_llm_client()
    player = st.session_state.get("player") or {}

    engine = GameEngine(
        scenario=scenario,
        llm_client=client,
        player_id=player.get("player_id"),
        codename=player.get("codename"),
    )
    if is_mock:
        engine.state.last_notice = (
            "Offline mock mode (no OPENAI_API_KEY found). "
            "Set OPENAI_API_KEY for live GPT-6 Luna dialogue, or present an inventory item to test progression."
        )
    st.session_state["_engine"] = engine
    st.session_state.pop("_saved_run_result", None)
    st.session_state.pop("_mock_ending", None)
    return {"ok": True, "error": None}


def get_mission_elapsed_seconds() -> int:
    """Return the running mission's elapsed seconds."""
    engine: Optional[GameEngine] = st.session_state.get("_engine")
    if engine is None:
        return 0
    return int(engine.elapsed_seconds())


def get_game_state() -> dict:
    """Return the full current gameplay UI state from the backend engine."""
    engine = _get_or_create_engine()
    return engine.get_ui_state()


def submit_response(text: str) -> dict:
    """Process one natural-language player turn and return the updated UI state."""
    engine = _get_or_create_engine()
    engine.submit_message(text)
    _persist_if_ended(engine)
    return engine.get_ui_state()


def use_item(item_id: str) -> dict:
    """Validate and apply an inventory item action and return the updated UI state."""
    engine = _get_or_create_engine()
    engine.use_item(item_id)
    _persist_if_ended(engine)
    return engine.get_ui_state()


def move_to_location(target_location: str) -> dict:
    """Validate and perform a location transition and return the updated UI state."""
    engine = _get_or_create_engine()
    engine.move_to(target_location)
    return engine.get_ui_state()


def take_gold_urn() -> dict:
    """Take the Gold Urn after clearing vault security and return updated UI state."""
    engine = _get_or_create_engine()
    engine.take_gold_urn()
    return engine.get_ui_state()


def trigger_voluntary_exit() -> dict:
    """Trigger the Alternate Ending voluntary exit when conditions are met."""
    engine = _get_or_create_engine()
    engine.trigger_voluntary_exit()
    _persist_if_ended(engine)
    return engine.get_ui_state()


def get_mission_result() -> dict:
    """Return the finished mission's debrief statistics and narrative outcome."""
    # Support BOBBERY_DEV_SHORTCUTS=1 manual ending preview
    dev_ending = st.session_state.get("_mock_ending")
    if dev_ending:
        engine = _get_or_create_engine()
        ending_id = _DEV_ENDING_MAP.get(dev_ending, "successful_infiltration")
        ending = engine.scenario.endings[ending_id]
        player = st.session_state.get("player") or {}
        best = (
            _get_db().get_personal_best(player["player_id"])
            if player.get("player_id")
            else None
        )
        return engine.endings.build_result_payload(
            state=engine.state,
            ending=ending,
            raw_seconds=engine.elapsed_seconds(),
            personal_best_seconds=best,
            is_new_record=False,
        )

    saved = st.session_state.get("_saved_run_result")
    if saved is not None:
        return saved

    engine = _get_or_create_engine()
    _persist_if_ended(engine)
    saved = st.session_state.get("_saved_run_result")
    if saved is not None:
        return saved

    player = st.session_state.get("player") or {}
    best = (
        _get_db().get_personal_best(player["player_id"])
        if player.get("player_id")
        else None
    )
    return engine.get_result(personal_best_seconds=best, is_new_record=False)
