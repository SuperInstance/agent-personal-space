"""Personal zones for agent space management."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ZoneType(Enum):
    """Privacy level of a zone."""
    PRIVATE = "private"       # Only the owner
    SHARED = "shared"         # Owner + explicitly granted agents
    PUBLIC = "public"         # All agents can access


@dataclass
class ZoneAccessRule:
    """An access rule within a zone.

    Defines what a specific agent (or all agents) can do within the zone.
    Permissions are strings like 'read', 'write', 'execute', etc.
    """
    agent_id: str | None = None  # None means applies to all
    permissions: set[str] = field(default_factory=set)
    resource_pattern: str = "*"  # Glob-style pattern for resources
    granted_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def matches_agent(self, agent_id: str) -> bool:
        """Check if this rule applies to the given agent."""
        return self.agent_id is None or self.agent_id == agent_id

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass
class PersonalZone:
    """A zone within an agent's personal space.

    Zones partition an agent's space into regions with different access
    levels. Each zone has a type (private/shared/public) and a set of
    access rules that govern what agents can do.
    """

    id: str
    owner_id: str
    zone_type: ZoneType
    name: str = ""
    description: str = ""
    access_rules: list[ZoneAccessRule] = field(default_factory=list)
    resources: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_access_rule(self, rule: ZoneAccessRule) -> None:
        """Add an access rule to this zone."""
        self.access_rules.append(rule)
        self.updated_at = time.time()

    def remove_access_rule(self, agent_id: str | None, permission: str) -> None:
        """Remove a specific permission for an agent."""
        for rule in self.access_rules:
            if rule.matches_agent(agent_id or "") or rule.agent_id == agent_id:
                rule.permissions.discard(permission)
        # Clean up empty rules
        self.access_rules = [r for r in self.access_rules if r.permissions]
        self.updated_at = time.time()

    def check_access(self, agent_id: str, permission: str, resource: str = "*") -> ZoneAccessResult:
        """Check if an agent has a specific permission in this zone.

        Returns a ZoneAccessResult with the decision and applicable rules.
        """
        # Owner always has full access
        if agent_id == self.owner_id:
            return ZoneAccessResult(
                allowed=True,
                reason="Owner has full access",
                zone_id=self.id,
                matching_rules=[],
            )

        # Private zones: only owner
        if self.zone_type == ZoneType.PRIVATE:
            return ZoneAccessResult(
                allowed=False,
                reason="Private zone — only owner has access",
                zone_id=self.id,
                matching_rules=[],
            )

        # Collect matching, non-expired rules
        matching: list[ZoneAccessRule] = []
        for rule in self.access_rules:
            if rule.is_expired():
                continue
            if not rule.matches_agent(agent_id):
                continue
            if rule.has_permission(permission):
                matching.append(rule)

        if matching:
            return ZoneAccessResult(
                allowed=True,
                reason=f"Access granted by {len(matching)} rule(s)",
                zone_id=self.id,
                matching_rules=matching,
            )

        # Public zones: allow if no explicit deny rules matched
        if self.zone_type == ZoneType.PUBLIC:
            return ZoneAccessResult(
                allowed=True,
                reason="Public zone — default allow",
                zone_id=self.id,
                matching_rules=[],
            )

        # Shared zone with no matching rules
        return ZoneAccessResult(
            allowed=False,
            reason="No access rule grants this permission",
            zone_id=self.id,
            matching_rules=[],
        )

    def grant_access(
        self,
        agent_id: str,
        permissions: set[str],
        expires_at: float | None = None,
    ) -> ZoneAccessRule:
        """Grant permissions to an agent in this zone."""
        # Find existing rule for this agent or create new
        for rule in self.access_rules:
            if rule.agent_id == agent_id and not rule.is_expired():
                rule.permissions.update(permissions)
                rule.expires_at = expires_at
                self.updated_at = time.time()
                return rule

        rule = ZoneAccessRule(
            agent_id=agent_id,
            permissions=permissions,
            expires_at=expires_at,
        )
        self.add_access_rule(rule)
        return rule

    def revoke_access(self, agent_id: str, permissions: set[str] | None = None) -> int:
        """Revoke permissions for an agent. If permissions is None, revoke all."""
        removed = 0
        updated_rules: list[ZoneAccessRule] = []
        for rule in self.access_rules:
            if rule.agent_id != agent_id:
                updated_rules.append(rule)
                continue
            if permissions is None:
                removed += len(rule.permissions)
                continue  # Drop the entire rule
            before = len(rule.permissions)
            rule.permissions -= permissions
            removed += before - len(rule.permissions)
            if rule.permissions:
                updated_rules.append(rule)

        self.access_rules = updated_rules
        self.updated_at = time.time()
        return removed

    def list_agents_with_access(self) -> set[str]:
        """Get all agent IDs that have active access rules."""
        agents: set[str] = set()
        for rule in self.access_rules:
            if not rule.is_expired() and rule.agent_id is not None:
                agents.add(rule.agent_id)
        return agents


@dataclass
class ZoneAccessResult:
    """Result of a zone access check."""
    allowed: bool
    reason: str
    zone_id: str
    matching_rules: list[ZoneAccessRule]
