"""One wall-clock allowance for all live model requests in a player turn."""

import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar

_deadline = ContextVar("llm_turn_deadline", default=None)
_requests = ThreadPoolExecutor(max_workers=8, thread_name_prefix="guard-request")


class TurnExpired(TimeoutError):
    """No time remains for a retry or another stage of this turn."""


@contextmanager
def turn_budget(seconds: float = 20):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


def remaining() -> float:
    deadline = _deadline.get()
    return float("inf") if deadline is None else max(0.0, deadline - time.monotonic())


def request(create, *, timeout, **kwargs):
    if _deadline.get() is None:  # Standalone client/CLI call
        return create(timeout=timeout, **kwargs)
    left = remaining()
    if left <= 0:
        raise TurnExpired("turn time budget exhausted")
    # SDK timeouts apply to individual network operations. Bound the caller's
    # total wait too, including queueing. Only the SDK runs in the worker;
    # a late reply can never modify game state.
    future = _requests.submit(create, timeout=min(timeout, left), **kwargs)
    try:
        return future.result(timeout=remaining())
    except TimeoutError as exc:
        if not future.done() or not remaining():
            future.cancel()
            raise TurnExpired("turn time budget exhausted") from exc
        raise
