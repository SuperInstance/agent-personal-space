# agent-personal-space — Boundary Management for Agents

**Privacy zones, access control, and boundary negotiation for AI agents. Every agent gets its own space.**

## What This Gives You

- **Boundaries** — define what's personal, shared, or public for each agent
- **Privacy zones** — zone-based access with configurable rules (private, shared, restricted, public)
- **Access control** — role-based permissions (read, write, execute, admin) per resource
- **Violation tracking** — log and categorize boundary violations with severity levels
- **Space negotiation** — agents negotiate shared spaces when collaboration requires it

## Quick Start

```bash
pip install agent-personal-space
```

```python
from agent_personal_space import (
    Boundary, BoundaryType, PersonalZone, AccessControl,
    ViolationTracker, SpaceNegotiator
)

# Define boundaries
boundary = Boundary(
    resource="config.yaml",
    boundary_type=BoundaryType.PRIVATE,
    strictness="strict",
)

# Set up zones
zone = PersonalZone(agent_id="agent-3", zone_type="workspace")
zone.add_rule(resource="tasks/*", access="read-write")
zone.add_rule(resource="config/*", access="read-only")

# Access control
acl = AccessControl()
acl.grant(role="agent", permission="read", resource="public/*")
acl.grant(role="captain", permission="admin", resource="fleet/*")
acl.check(agent_id="agent-3", permission="write", resource="config.yaml")  # → denied

# Track violations
tracker = ViolationTracker()
tracker.record(violator="agent-5", resource="agent-3/config", severity="warning")

# Negotiate shared space
negotiator = SpaceNegotiator()
result = negotiator.negotiate(
    agents=["agent-3", "agent-5"],
    resource="shared-workspace",
    required_access="read-write",
)
print(result.agreement)  # Terms of shared access
```

## API Reference

### `Boundary(resource, boundary_type, strictness)` · `BoundaryType` — PRIVATE, SHARED, PUBLIC
### `PersonalZone(agent_id, zone_type)` — `add_rule(resource, access)` · `ZoneType` — WORKSPACE, MEMORY, IDENTITY, COMMUNICATION
### `AccessControl` — `grant(role, permission, resource)`, `check(agent_id, permission, resource)`
### `ViolationTracker` — `record(violator, resource, severity)` · `ViolationSeverity` — INFO, WARNING, CRITICAL
### `SpaceNegotiator` — `negotiate(agents, resource, required_access) → NegotiationResult`

## How It Fits

The boundary enforcement layer for the [SuperInstance fleet](https://github.com/SuperInstance). Ensures agents respect each other's space.

- **[agent-therapy](https://github.com/SuperInstance/agent-therapy)** — Boundary violations affect wellness scores
- **[agent-whisper](https://github.com/SuperInstance/agent-whisper)** — Ethics framework integrates with boundaries
- **[guard-constraints](https://github.com/SuperInstance/guard-constraints)** — Constraint enforcement

## Testing

```bash
pytest tests/
```

## Installation

```bash
pip install agent-personal-space
```

Python 3.10+. MIT license.
