"""LLM layer for Bobbery Rob.

The LLM is a function, not an agent: it interprets the player's message and
writes guard dialogue. It never changes game state; the engine does.

Use `get_client()` to get the real client or the mock.
"""

import os

from llm.client import LLMClient
from llm.mock_client import MockLLMClient


def get_client(mock: bool | None = None) -> LLMClient | MockLLMClient:
    """Return the mock when `mock` is True or BOBBERY_LLM_MOCK=1, else the real client.

    The real client raises RuntimeError here (at startup, not mid-game) if no
    API key is configured.
    """
    if mock is None:
        mock = os.getenv("BOBBERY_LLM_MOCK") == "1"
    return MockLLMClient() if mock else LLMClient()


__all__ = ["LLMClient", "MockLLMClient", "get_client"]
