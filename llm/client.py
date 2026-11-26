"""Thin wrapper around the GPT-6 Luna API (OpenAI Responses API).

The client never raises into the game loop. After a limited number of retries
it returns a safe fallback and records the problem in `last_error`.

API details (OpenAI docs, gpt-6-luna model page and Structured Outputs guide):
- model id `gpt-6-luna`
- `reasoning.effort`: none | low | medium (default) | high | xhigh | max
- strict JSON output via `text={"format": {"type": "json_schema", ...}}`
- the reply text is read from `response.output_text`
"""

import json
import logging
import os
import time
from typing import Any

from llm import budget, prompts, schemas

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-6-luna"
EFFORT_ANALYSIS = "low"
EFFORT_DIALOGUE = "low"
EFFORT_EVALUATION = "high"


def read_setting(name: str) -> str | None:
    """Read a setting from the environment, then from Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name)
    except (ImportError, FileNotFoundError):  # no Streamlit, or no secrets.toml
        return None


class LLMClient:
    """Real client. Same public methods as `MockLLMClient`."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 20.0,
        max_retries: int = 2,
        sdk_client: Any = None,
    ) -> None:
        self.model = model or read_setting("BOBBERY_LLM_MODEL") or DEFAULT_MODEL
        self.max_retries = max_retries
        self.timeout = timeout
        self.last_error: str | None = None
        self._use_chat_completions = False

        if sdk_client is not None:  # tests inject a fake here
            self._sdk = sdk_client
            return

        api_key = api_key or read_setting("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No API key. Set OPENAI_API_KEY in the environment or in "
                ".streamlit/secrets.toml, or use the mock client."
            )
        from openai import OpenAI

        base_url = read_setting("OPENAI_BASE_URL")
        # OpenAI-compatible proxies typically expose /chat/completions rather than /responses.
        self._use_chat_completions = bool(base_url)

        # Retries are done here so that invalid JSON is retried too.
        self._sdk = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
        )

    # ------------------------------------------------------------------ calls

    def analyze(self, player_message: str, context: dict[str, Any]) -> dict[str, Any]:
        """Call A. Returns a grounded analysis dict, plus `"fallback": bool`."""
        instructions, input_text = prompts.build_analysis_prompt(player_message, context)
        data = self._call_json(
            instructions,
            input_text,
            "bobbery_analysis",
            schemas.ANALYSIS_SCHEMA,
            schemas.analysis_errors,
            EFFORT_ANALYSIS,
        )
        if data is None:
            return schemas.fallback_analysis()
        claim_ids, turn_ids, item_ids = prompts.known_ids(context)
        return schemas.ground_analysis(data, claim_ids, turn_ids, item_ids)

    def write_dialogue(
        self,
        player_message: str,
        outcome: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Call B. Returns the guard's line, or a neutral fallback line."""
        instructions, input_text = prompts.build_dialogue_prompt(player_message, outcome, context)
        for attempt in range(self.max_retries + 1):
            try:
                text = self._request(instructions, input_text, EFFORT_DIALOGUE, None)
                line = schemas.clean_dialogue(text)
                if line:
                    self.last_error = None
                    return line
                self.last_error = "empty dialogue reply"
            except budget.TurnExpired as exc:
                self.last_error = str(exc)
                break
            except Exception as exc:  # noqa: BLE001 - provider errors must return neutral dialogue
                self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("dialogue attempt %d failed: %s", attempt + 1, self.last_error)
            _backoff(attempt, self.max_retries)
        return schemas.FALLBACK_DIALOGUE

    def evaluate_explanation(self, explanation: str, context: dict[str, Any]) -> dict[str, Any]:
        """Call C. Returns an evaluation dict, plus `"fallback": bool`."""
        instructions, input_text = prompts.build_evaluation_prompt(explanation, context)
        data = self._call_json(
            instructions,
            input_text,
            "bobbery_evaluation",
            schemas.EVALUATION_SCHEMA,
            schemas.evaluation_errors,
            EFFORT_EVALUATION,
        )
        if data is None:
            return schemas.fallback_evaluation()
        _, turn_ids, _ = prompts.known_ids(context)
        return schemas.ground_evaluation(data, turn_ids)

    # --------------------------------------------------------------- plumbing

    def _call_json(self, instructions, input_text, name, schema, check, effort):
        """Request strict JSON, parse and validate it. Returns None on failure."""
        text_format = {"type": "json_schema", "name": name, "schema": schema, "strict": True}
        for attempt in range(self.max_retries + 1):
            try:
                text = self._request(instructions, input_text, effort, text_format)
                data = json.loads(_strip_json_fences(text) if self._use_chat_completions else text)
                errors = check(data)
                if not errors:
                    self.last_error = None
                    return data
                self.last_error = "schema: " + "; ".join(errors[:3])
            except budget.TurnExpired as exc:
                self.last_error = str(exc)
                break
            except Exception as exc:  # noqa: BLE001 - invalid model output or provider failure
                self.last_error = f"{type(exc).__name__}: {exc}"
            log.warning("%s attempt %d failed: %s", name, attempt + 1, self.last_error)
            _backoff(attempt, self.max_retries)
        return None

    def _request(self, instructions, input_text, effort, text_format) -> str:
        if self._use_chat_completions:
            return self._request_chat(instructions, input_text, effort, text_format)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input_text,
            "reasoning": {"effort": effort},
            "max_output_tokens": 8000 if effort == "high" else 3000,
        }
        if text_format is not None:
            kwargs["text"] = {"format": text_format}
        try:
            response = budget.request(self._sdk.responses.create, timeout=self.timeout, **kwargs)
        except Exception as exc:
            if type(exc).__name__ == "NotFoundError" and hasattr(self._sdk, "chat"):
                log.info("Responses API returned 404; switching to Chat Completions API.")
                self._use_chat_completions = True
                return self._request_chat(instructions, input_text, effort, text_format)
            raise
        text = getattr(response, "output_text", None)
        if not text:
            status = getattr(response, "status", "unknown")
            raise ValueError(f"no output text (status={status}, maybe a refusal)")
        return text

    def _request_chat(self, instructions, input_text, effort, text_format) -> str:
        system_content = instructions
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 2000 if effort == "high" else 1000,
        }
        if text_format is not None:
            schema_json = json.dumps(text_format["schema"], ensure_ascii=False)
            system_content = (
                f"{instructions}\n\n"
                "You MUST respond with a single raw JSON object (no markdown fences) "
                f"strictly conforming to this JSON Schema:\n{schema_json}"
            )
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": text_format["name"],
                    "schema": text_format["schema"],
                    "strict": True,
                },
            }
        kwargs["messages"] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": input_text},
        ]
        response = budget.request(self._sdk.chat.completions.create, timeout=self.timeout, **kwargs)
        choices = getattr(response, "choices", None) or []
        message = getattr(choices[0], "message", None) if choices else None
        text = getattr(message, "content", None)
        if not text:
            raise ValueError("no message content returned from chat.completions")
        return text


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _backoff(attempt: int, max_retries: int) -> None:
    if attempt < max_retries:
        time.sleep(min(0.5 * (attempt + 1), budget.remaining()))
