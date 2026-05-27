"""Boundary definitions for agent personal space."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class BoundaryType(Enum):
    """What kind of boundary this is."""
    DATA_ACCESS = "data_access"
    COMMUNICATION = "communication"
    RESOURCE = "resource"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    BEHAVIORAL = "behavioral"


class Strictness(Enum):
    """How strictly a boundary is enforced."""
    ADVISORY = "advisory"       # Logged but not blocked
    MODERATE = "moderate"       # Requires justification
    STRICT = "strict"           # Blocked unless explicitly exempted
    ABSOLUTE = "absolute"       # Cannot be overridden


@dataclass
class Boundary:
    """A single boundary rule for an agent.

    Boundaries define what is and isn't allowed within an agent's personal
    space. Each boundary has a type, strictness level, optional conditions
    for when it applies, and a list of exempt agents.
    """

    id: str
    owner_id: str
    boundary_type: BoundaryType
    strictness: Strictness
    description: str = ""
    conditions: dict[str, Any] = field(default_factory=dict)
    exceptions: list[str] = field(default_factory=list)  # agent IDs exempted
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if this boundary has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_agent_exempted(self, agent_id: str) -> bool:
        """Check if an agent is exempted from this boundary."""
        return agent_id in self.exceptions

    def check_conditions(self, context: dict[str, Any]) -> bool:
        """Check if all conditions are satisfied in the given context.

        Conditions are key-value pairs where the key is a context field name
        and the value is either an exact value or a callable predicate.
        """
        for key, expected in self.conditions.items():
            actual = context.get(key)
            if callable(expected):
                if not expected(actual):
                    return False
            elif actual != expected:
                return False
        return True

    def evaluate(self, agent_id: str, context: dict[str, Any] | None = None) -> BoundaryDecision:
        """Evaluate whether an agent is allowed to cross this boundary.

        Returns a BoundaryDecision with the result and reason.
        """
        if self.is_expired():
            return BoundaryDecision(allowed=True, reason="Boundary has expired", boundary=self)

        if agent_id == self.owner_id:
            return BoundaryDecision(allowed=True, reason="Owner always has access", boundary=self)

        if self.is_agent_exempted(agent_id):
            return BoundaryDecision(allowed=True, reason=f"Agent {agent_id} is exempted", boundary=self)

        if context and not self.check_conditions(context):
            return BoundaryDecision(
                allowed=True,
                reason="Conditions not met — boundary does not apply",
                boundary=self,
            )

        strictness_messages = {
            Strictness.ADVISORY: "Advisory boundary — logged but allowed",
            Strictness.MODERATE: "Moderate boundary — requires justification",
            Strictness.STRICT: "Strict boundary — access denied",
            Strictness.ABSOLUTE: "Absolute boundary — cannot be overridden",
        }

        allowed = self.strictness in (Strictness.ADVISORY,)
        return BoundaryDecision(
            allowed=allowed,
            reason=strictness_messages[self.strictness],
            boundary=self,
        )

    def add_exception(self, agent_id: str) -> None:
        """Add an agent to the exceptions list."""
        if agent_id not in self.exceptions:
            self.exceptions.append(agent_id)
            self.updated_at = time.time()

    def remove_exception(self, agent_id: str) -> None:
        """Remove an agent from the exceptions list."""
        self.exceptions = [a for a in self.exceptions if a != agent_id]
        self.updated_at = time.time()


@dataclass
class BoundaryDecision:
    """Result of evaluating a boundary check."""
    allowed: bool
    reason: str
    boundary: Boundary
