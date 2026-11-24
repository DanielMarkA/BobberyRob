"""Suspicion scoring, clamping, and threshold evaluation."""

from scenario.loader import SuspicionSettings, SuspicionThreshold

# Extra deterministic engine events not always listed in scenario event_table.
DEFAULT_EXTRA_EVENTS: dict[str, int] = {
    "false_action_claim": 15,
}


class SuspicionManager:
    """Owns all suspicion math and tier resolution based on scenario config."""

    def __init__(self, settings: SuspicionSettings) -> None:
        self._settings = settings

    @property
    def starting_value(self) -> int:
        return self._settings.starting_value

    @property
    def min_value(self) -> int:
        return self._settings.min_value

    @property
    def max_value(self) -> int:
        return self._settings.max_value

    def clamp(self, value: int) -> int:
        return max(self.min_value, min(self.max_value, int(value)))

    def apply_delta(self, current: int, delta: int) -> tuple[int, int]:
        """Apply a signed delta, clamp to bounds, and return (new_value, applied_delta)."""
        clamped = self.clamp(current + delta)
        return clamped, clamped - current

    def event_delta(self, event_name: str) -> int:
        """Look up the configured suspicion delta for a named game event."""
        if event_name in self._settings.event_table:
            return int(self._settings.event_table[event_name]["delta"])
        if event_name in DEFAULT_EXTRA_EVENTS:
            return DEFAULT_EXTRA_EVENTS[event_name]
        raise KeyError(f"Unknown suspicion event: '{event_name}'")

    def apply_event(self, current: int, event_name: str) -> tuple[int, int]:
        """Apply a named scenario suspicion event and return (new_value, applied_delta)."""
        delta = self.event_delta(event_name)
        return self.apply_delta(current, delta)

    def threshold_for(self, value: int) -> SuspicionThreshold:
        """Return the SuspicionThreshold matching the given value."""
        clamped = self.clamp(value)
        for threshold in self._settings.thresholds:
            low, high = threshold.range[0], threshold.range[1]
            if low <= clamped <= high:
                return threshold
        return self._settings.thresholds[-1]

    def label_for(self, value: int) -> str:
        return self.threshold_for(value).label

    def tier_for(self, value: int) -> str:
        return self.threshold_for(value).tier

    def is_mandatory_interrogation(self, value: int) -> bool:
        return self.clamp(value) >= 60

    def is_final_interrogation(self, value: int) -> bool:
        return self.clamp(value) >= self.max_value
