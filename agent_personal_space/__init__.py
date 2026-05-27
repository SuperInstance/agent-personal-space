"""Agent Personal Space — boundary management, privacy zones, and access control for AI agents."""

from agent_personal_space.boundary import Boundary, BoundaryType, Strictness
from agent_personal_space.zone import PersonalZone, ZoneType, ZoneAccessRule
from agent_personal_space.access import AccessControl, Permission, Role
from agent_personal_space.violations import ViolationTracker, Violation, ViolationSeverity
from agent_personal_space.negotiator import SpaceNegotiator, NegotiationResult

__version__ = "0.1.0"
__all__ = [
    "Boundary", "BoundaryType", "Strictness",
    "PersonalZone", "ZoneType", "ZoneAccessRule",
    "AccessControl", "Permission", "Role",
    "ViolationTracker", "Violation", "ViolationSeverity",
    "SpaceNegotiator", "NegotiationResult",
]
