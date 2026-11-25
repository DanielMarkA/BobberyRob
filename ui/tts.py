"""Neural Text-to-Speech (edge-tts) for Bobbery Rob security guards.

Synthesizes guard dialogue with distinct personality-matched Microsoft neural
voices (free, no API key required) and caches audio bytes across reruns.
Falls back cleanly to None so the browser audio controller can use Web Speech.
"""

import asyncio
import base64
import concurrent.futures
import logging
from typing import Optional

import streamlit as st

log = logging.getLogger(__name__)

# Personality-matched neural voice presets for every guard in scenario/museum.json
GUARD_VOICES: dict[str, dict[str, str]] = {
    "guard_casual": {
        "voice": "en-US-AndrewNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
    },
    "guard_strict": {
        "voice": "en-GB-RyanNeural",
        "rate": "-4%",
        "pitch": "-4Hz",
    },
    "guard_observant": {
        "voice": "en-US-AvaNeural",
        "rate": "+2%",
        "pitch": "+0Hz",
    },
    "guard_experienced": {
        "voice": "en-US-BrianNeural",
        "rate": "-6%",
        "pitch": "-6Hz",
    },
    "guard_impatient": {
        "voice": "en-US-ChristopherNeural",
        "rate": "+14%",
        "pitch": "+2Hz",
    },
    "guard_exit": {
        "voice": "en-US-EricNeural",
        "rate": "-2%",
        "pitch": "-4Hz",
    },
    "guard_interrogator": {
        "voice": "en-GB-ThomasNeural",
        "rate": "+4%",
        "pitch": "-6Hz",
    },
}

SPEAKER_TO_GUARD_ID: dict[str, str] = {
    "Officer Miller": "guard_casual",
    "Officer Graves": "guard_strict",
    "Inspector Lin": "guard_observant",
    "Chief Sterling": "guard_experienced",
    "Officer Gomez": "guard_impatient",
    "Captain Reyes": "guard_exit",
    "Chief Investigator": "guard_interrogator",
}

DEFAULT_VOICE = {"voice": "en-US-AndrewNeural", "rate": "+0%", "pitch": "+0Hz"}


def resolve_guard_id(guard_id: Optional[str] = None, speaker: Optional[str] = None) -> str:
    if guard_id and guard_id in GUARD_VOICES:
        return guard_id
    if speaker and speaker in SPEAKER_TO_GUARD_ID:
        return SPEAKER_TO_GUARD_ID[speaker]
    return "guard_casual"


TTS_TIMEOUT_SECONDS = 5.0


async def _synthesize_bytes_async(text: str, voice: str, rate: str, pitch: str) -> bytes:
    import edge_tts

    async def _collect() -> bytes:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio" and chunk.get("data"):
                chunks.append(chunk["data"])
        return b"".join(chunks)

    return await asyncio.wait_for(_collect(), timeout=TTS_TIMEOUT_SECONDS)


def _run_async(coro) -> bytes:
    """Run an async coroutine safely whether or not a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=TTS_TIMEOUT_SECONDS + 1.0)


@st.cache_data(max_entries=128, show_spinner=False)
def synthesize_guard_speech_uri(text: str, guard_id: str) -> Optional[str]:
    """Generate a base64 MP3 data URI for a guard utterance, or None on failure."""
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    preset = GUARD_VOICES.get(guard_id, DEFAULT_VOICE)
    try:
        audio_bytes = _run_async(
            _synthesize_bytes_async(
                cleaned,
                voice=preset["voice"],
                rate=preset["rate"],
                pitch=preset["pitch"],
            )
        )
        if not audio_bytes:
            return None
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        return f"data:audio/mpeg;base64,{b64}"
    except Exception as exc:
        log.warning("edge-tts synthesis failed (%s): %s", guard_id, exc)
        return None
