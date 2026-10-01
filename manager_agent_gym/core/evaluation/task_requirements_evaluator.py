"""
Deterministic per-task checklist scoring.

A task's score is items passed / total items (docs/team_non_stationarity/metrics.md).
Pure functions over plain data, so they run on already-generated run outputs without
the engine or any LLM call.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...schemas.core.tasks import TaskRequirement


@dataclass(frozen=True)
class ChecklistResult:
    passed: int
    total: int
    failed_keys: tuple[str, ...] = ()

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0


def task_output_text(
    output_resource_ids: Iterable[str], resources: Mapping[str, Mapping]
) -> str:
    """Concatenate the text content of a task's output resources (missing ids skipped)."""
    parts: list[str] = []
    for rid in output_resource_ids:
        content = (resources.get(str(rid)) or {}).get("content")
        if isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def score_checklist(
    requirements: Iterable[TaskRequirement], output_text: str
) -> ChecklistResult:
    """Score every requirement against `output_text`.

    Raises ValueError if a requirement has no pattern, so a prose-only item can't be
    silently scored as a failure.
    """
    reqs = list(requirements)
    failed = tuple(r.key for r in reqs if not r.passes(output_text))
    return ChecklistResult(
        passed=len(reqs) - len(failed), total=len(reqs), failed_keys=failed
    )
