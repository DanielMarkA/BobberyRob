"""Guard memory and shared security reports for Bobbery Rob."""

from collections.abc import Callable
from typing import Any

from memory.archive import Archive
from memory.claims import ClaimStore
from memory.models import Report


class GuardMemory:
    """Manages shared security reports and guard viewpoints."""

    def __init__(self, reports: list[Report] | None = None) -> None:
        self._reports = list(reports or [])
        self._next_id = max((r.report_id for r in self._reports), default=0) + 1

    def add_report(
        self,
        source_turn: int,
        summary: str,
        shared_with: list[str] | None = None,
        turn_validator: Callable[[int], bool] | None = None,
    ) -> Report:
        """Add a shared security report."""
        if turn_validator is not None and not turn_validator(source_turn):
            raise ValueError(
                f"Source turn {source_turn} does not exist in the conversation archive."
            )

        guards = list(shared_with) if shared_with is not None else []
        report = Report(
            report_id=self._next_id,
            source_turn=source_turn,
            summary=summary,
            shared_with=guards,
        )
        self._reports.append(report)
        self._next_id += 1
        return report

    def reports_for_guard(self, guard_id: str) -> list[Report]:
        """Return reports shared with this guard or with all guards (empty shared_with)."""
        return [r for r in self._reports if len(r.shared_with) == 0 or guard_id in r.shared_with]

    def guard_view(
        self,
        guard_id: str,
        archive: Archive,
        claim_store: ClaimStore,
    ) -> dict[str, Any]:
        """Return a guard's perspective.

        Includes:
        - 'turns': turns this guard witnessed
        - 'claims': claims made during those witnessed turns
        - 'reports': reports shared with this guard or with everyone
        """
        witnessed_turns = archive.turns_for_guard(guard_id)
        witnessed_turn_ids = {t.turn_id for t in witnessed_turns}
        witnessed_claims = [
            c for c in claim_store.all_claims() if c.source_turn in witnessed_turn_ids
        ]
        relevant_reports = self.reports_for_guard(guard_id)

        return {
            "turns": witnessed_turns,
            "claims": witnessed_claims,
            "reports": relevant_reports,
        }

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialize all reports to plain dictionaries."""
        return [r.to_dict() for r in self._reports]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> "GuardMemory":
        """Deserialize guard memory from a list of report dictionaries."""
        reports = [Report.from_dict(item) for item in data]
        return cls(reports=reports)
