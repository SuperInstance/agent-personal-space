"""Violation tracking for boundary breaches."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ViolationSeverity(Enum):
    """Severity levels for violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def numeric(self) -> int:
        mapping = {
            ViolationSeverity.LOW: 1,
            ViolationSeverity.MEDIUM: 2,
            ViolationSeverity.HIGH: 3,
            ViolationSeverity.CRITICAL: 4,
        }
        return mapping[self]


@dataclass
class Violation:
    """Record of a boundary violation."""
    id: str
    violator_id: str
    boundary_id: str
    severity: ViolationSeverity
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: float | None = None
    resolution_note: str = ""

    def resolve(self, note: str = "") -> None:
        """Mark this violation as resolved."""
        self.resolved = True
        self.resolved_at = time.time()
        self.resolution_note = note


class ViolationTracker:
    """Tracks and manages boundary violations.

    Provides methods to log violations, query history, check agent
    standing, and generate summaries.
    """

    def __init__(self, max_violations: int = 10000) -> None:
        self._violations: list[Violation] = []
        self._next_id = 1
        self._max_violations = max_violations

    def record(
        self,
        violator_id: str,
        boundary_id: str,
        severity: ViolationSeverity = ViolationSeverity.MEDIUM,
        description: str = "",
        context: dict[str, Any] | None = None,
    ) -> Violation:
        """Record a new violation."""
        violation = Violation(
            id=str(self._next_id),
            violator_id=violator_id,
            boundary_id=boundary_id,
            severity=severity,
            description=description,
            context=context or {},
        )
        self._next_id += 1
        self._violations.append(violation)

        # Evict oldest if at capacity
        if len(self._violations) > self._max_violations:
            self._violations = self._violations[-self._max_violations:]

        return violation

    def get_violations(
        self,
        violator_id: str | None = None,
        boundary_id: str | None = None,
        severity: ViolationSeverity | None = None,
        resolved: bool | None = None,
        since: float | None = None,
    ) -> list[Violation]:
        """Query violations with optional filters."""
        results = self._violations
        if violator_id is not None:
            results = [v for v in results if v.violator_id == violator_id]
        if boundary_id is not None:
            results = [v for v in results if v.boundary_id == boundary_id]
        if severity is not None:
            results = [v for v in results if v.severity == severity]
        if resolved is not None:
            results = [v for v in results if v.resolved == resolved]
        if since is not None:
            results = [v for v in results if v.timestamp >= since]
        return results

    def get_agent_standing(self, agent_id: str) -> AgentStanding:
        """Get the standing of an agent based on their violation history."""
        agent_violations = [v for v in self._violations if v.violator_id == agent_id]
        unresolved = [v for v in agent_violations if not v.resolved]

        if not agent_violations:
            return AgentStanding(
                agent_id=agent_id,
                total_violations=0,
                unresolved_count=0,
                worst_severity=None,
                status="clean",
            )

        worst = max(agent_violations, key=lambda v: v.severity.numeric)

        score = sum(v.severity.numeric for v in unresolved)
        if score == 0:
            status = "clean"
        elif score <= 2:
            status = "warning"
        elif score <= 5:
            status = "restricted"
        else:
            status = "banned"

        return AgentStanding(
            agent_id=agent_id,
            total_violations=len(agent_violations),
            unresolved_count=len(unresolved),
            worst_severity=worst.severity,
            status=status,
        )

    def resolve_violation(self, violation_id: str, note: str = "") -> Violation | None:
        """Resolve a violation by ID."""
        for v in self._violations:
            if v.id == violation_id:
                v.resolve(note)
                return v
        return None

    def summary(self) -> ViolationSummary:
        """Generate a summary of all tracked violations."""
        by_severity: dict[ViolationSeverity, int] = {}
        for severity in ViolationSeverity:
            by_severity[severity] = len([v for v in self._violations if v.severity == severity])

        total = len(self._violations)
        resolved = len([v for v in self._violations if v.resolved])

        return ViolationSummary(
            total=total,
            resolved=resolved,
            unresolved=total - resolved,
            by_severity=by_severity,
            unique_violators=len({v.violator_id for v in self._violations}),
        )


@dataclass
class AgentStanding:
    """Standing assessment for an agent."""
    agent_id: str
    total_violations: int
    unresolved_count: int
    worst_severity: ViolationSeverity | None
    status: str  # "clean", "warning", "restricted", "banned"


@dataclass
class ViolationSummary:
    """Aggregate summary of violations."""
    total: int
    resolved: int
    unresolved: int
    by_severity: dict[ViolationSeverity, int]
    unique_violators: int
