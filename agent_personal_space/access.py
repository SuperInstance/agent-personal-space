"""Access control with roles, permissions, and time-limited grants."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Permission(Enum):
    """Standard permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"
    INVITE = "invite"


class Role(Enum):
    """Predefined roles with associated permissions."""
    OWNER = "owner"
    ADMIN = "admin"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"
    GUEST = "guest"

    @property
    def default_permissions(self) -> set[Permission]:
        mapping: dict[Role, set[Permission]] = {
            Role.OWNER: set(Permission),
            Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.DELETE, Permission.SHARE, Permission.INVITE},
            Role.COLLABORATOR: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
            Role.VIEWER: {Permission.READ},
            Role.GUEST: {Permission.READ},
        }
        return mapping[self]


@dataclass
class Grant:
    """A permission grant from one agent to another."""
    grantor_id: str
    grantee_id: str
    permissions: set[Permission]
    resource: str = "*"
    granted_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_active(self) -> bool:
        return not self.is_expired()


@dataclass
class RoleAssignment:
    """A role assigned to an agent for a resource."""
    agent_id: str
    role: Role
    resource: str = "*"
    assigned_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class AccessControl:
    """Manages permissions, roles, and access grants for agents.

    Provides a unified interface for checking whether an agent has
    permission to perform an action on a resource.
    """

    def __init__(self) -> None:
        self._grants: list[Grant] = []
        self._roles: list[RoleAssignment] = []
        self._revoked: set[tuple[str, str, str]] = set()  # (grantor, grantee, resource)

    def grant(
        self,
        grantor_id: str,
        grantee_id: str,
        permissions: set[Permission],
        resource: str = "*",
        expires_at: float | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> Grant:
        """Grant permissions to an agent."""
        grant = Grant(
            grantor_id=grantor_id,
            grantee_id=grantee_id,
            permissions=permissions,
            resource=resource,
            expires_at=expires_at,
            conditions=conditions or {},
        )
        self._grants.append(grant)
        # Clear any prior revocation
        self._revoked.discard((grantor_id, grantee_id, resource))
        return grant

    def revoke(self, grantor_id: str, grantee_id: str, resource: str = "*") -> int:
        """Revoke all grants from grantor to grantee for a resource."""
        self._revoked.add((grantor_id, grantee_id, resource))
        count = 0
        for g in self._grants:
            if g.grantor_id == grantor_id and g.grantee_id == grantee_id and g.resource == resource:
                count += 1
        return count

    def assign_role(
        self,
        agent_id: str,
        role: Role,
        resource: str = "*",
        expires_at: float | None = None,
    ) -> RoleAssignment:
        """Assign a role to an agent."""
        assignment = RoleAssignment(
            agent_id=agent_id,
            role=role,
            resource=resource,
            expires_at=expires_at,
        )
        self._roles.append(assignment)
        return assignment

    def check(self, agent_id: str, permission: Permission, resource: str = "*") -> AccessResult:
        """Check if an agent has a specific permission on a resource.

        Checks grants first, then role-based permissions.
        """
        # Check grants
        for grant in reversed(self._grants):
            if not grant.is_active():
                continue
            if grant.grantee_id != agent_id:
                continue
            if not self._resource_matches(grant.resource, resource):
                continue
            if (grant.grantor_id, grant.grantee_id, grant.resource) in self._revoked:
                continue
            if permission in grant.permissions:
                return AccessResult(
                    allowed=True,
                    reason=f"Granted by {grant.grantor_id}",
                    source="grant",
                )

        # Check roles
        for assignment in self._roles:
            if assignment.is_expired():
                continue
            if assignment.agent_id != agent_id:
                continue
            if not self._resource_matches(assignment.resource, resource):
                continue
            if permission in assignment.role.default_permissions:
                return AccessResult(
                    allowed=True,
                    reason=f"Role: {assignment.role.value}",
                    source="role",
                )

        return AccessResult(
            allowed=False,
            reason="No matching grant or role found",
            source="none",
        )

    def get_agent_permissions(self, agent_id: str, resource: str = "*") -> set[Permission]:
        """Get all active permissions for an agent on a resource."""
        perms: set[Permission] = set()

        for grant in self._grants:
            if not grant.is_active():
                continue
            if grant.grantee_id != agent_id:
                continue
            if not self._resource_matches(grant.resource, resource):
                continue
            if (grant.grantor_id, grant.grantee_id, grant.resource) in self._revoked:
                continue
            perms.update(grant.permissions)

        for assignment in self._roles:
            if assignment.is_expired():
                continue
            if assignment.agent_id != agent_id:
                continue
            if not self._resource_matches(assignment.resource, resource):
                continue
            perms.update(assignment.role.default_permissions)

        return perms

    def list_grants(self, agent_id: str | None = None) -> list[Grant]:
        """List all active grants, optionally filtered by grantee."""
        result = []
        for g in self._grants:
            if g.is_expired():
                continue
            if (g.grantor_id, g.grantee_id, g.resource) in self._revoked:
                continue
            if agent_id is None or g.grantee_id == agent_id:
                result.append(g)
        return result

    def cleanup_expired(self) -> int:
        """Remove expired grants and role assignments. Returns count of removed items."""
        before_grants = len(self._grants)
        before_roles = len(self._roles)
        self._grants = [g for g in self._grants if g.is_active()]
        self._roles = [r for r in self._roles if not r.is_expired()]
        return (before_grants - len(self._grants)) + (before_roles - len(self._roles))

    @staticmethod
    def _resource_matches(pattern: str, resource: str) -> bool:
        """Check if a resource matches a pattern. '*' matches everything."""
        if pattern == "*":
            return True
        return pattern == resource


@dataclass
class AccessResult:
    """Result of an access check."""
    allowed: bool
    reason: str
    source: str  # "grant", "role", "none"
