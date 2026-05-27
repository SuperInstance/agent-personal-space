# agent-personal-space

**Boundary management, privacy zones, and access control for AI agents.**

A Python library that gives AI agents personal space — defining boundaries, managing privacy zones, controlling access, tracking violations, and negotiating shared spaces.

Part of the [Cocapn fleet](https://github.com/Lucineer/the-fleet).

## Installation

```bash
pip install agent-personal-space
```

## Quick Start

### Boundaries

```python
from agent_personal_space import Boundary, BoundaryType, Strictness

# Create a strict data access boundary
boundary = Boundary(
    id="data-1",
    owner_id="agent-alice",
    boundary_type=BoundaryType.DATA_ACCESS,
    strictness=Strictness.STRICT,
    description="Alice's data cannot be accessed without consent",
)

# Evaluate access
decision = boundary.evaluate("agent-bob")
print(decision.allowed)   # False
print(decision.reason)    # "Strict boundary — access denied"

# Add exemptions
boundary.add_exception("agent-bob")
decision = boundary.evaluate("agent-bob")
print(decision.allowed)   # True
```

### Privacy Zones

```python
from agent_personal_space import PersonalZone, ZoneType

zone = PersonalZone(
    id="workspace",
    owner_id="agent-alice",
    zone_type=ZoneType.SHARED,
    name="Alice's Workspace",
)

# Grant access to another agent
zone.grant_access("agent-bob", {"read", "write"})

# Check permissions
result = zone.check_access("agent-bob", "read")
print(result.allowed)  # True

result = zone.check_access("agent-bob", "delete")
print(result.allowed)  # False

# Time-limited access
import time
zone.grant_access("agent-carol", {"read"}, expires_at=time.time() + 3600)
```

### Access Control

```python
from agent_personal_space import AccessControl, Permission, Role

ac = AccessControl()

# Grant specific permissions
ac.grant("agent-alice", "agent-bob", {Permission.READ, Permission.WRITE})

# Or assign roles
ac.assign_role("agent-carol", Role.VIEWER)

# Check access
result = ac.check("agent-bob", Permission.WRITE)
print(result.allowed)  # True

result = ac.check("agent-carol", Permission.DELETE)
print(result.allowed)  # False

# Time-limited grants
ac.grant("agent-alice", "agent-dave", {Permission.READ}, expires_at=time.time() + 3600)
```

### Violation Tracking

```python
from agent_personal_space import ViolationTracker, ViolationSeverity

tracker = ViolationTracker()

# Record violations
tracker.record("agent-bob", "data-1", ViolationSeverity.HIGH, "Unauthorized data access")

# Check agent standing
standing = tracker.get_agent_standing("agent-bob")
print(standing.status)  # "restricted"
print(standing.total_violations)  # 1

# Resolve violations
violations = tracker.get_violations(resolved=False)
tracker.resolve_violation(violations[0].id, "Incident resolved")
```

### Space Negotiation

```python
from agent_personal_space import SpaceNegotiator, BoundaryType, Strictness, ZoneType
from agent_personal_space import Boundary, PersonalZone

negotiator = SpaceNegotiator()

# Agent A proposes shared boundaries
negotiation = negotiator.propose(
    proposer_id="agent-alice",
    target_id="agent-bob",
    boundaries=[Boundary(id="shared-data", owner_id="agent-alice",
                         boundary_type=BoundaryType.DATA_ACCESS,
                         strictness=Strictness.STRICT)],
    zones=[PersonalZone(id="shared-zone", owner_id="agent-alice",
                        zone_type=ZoneType.SHARED)],
)

# Agent B counters with different terms
negotiator.counter(negotiation.id, "agent-bob",
    boundaries=[Boundary(id="shared-data", owner_id="agent-bob",
                         boundary_type=BoundaryType.DATA_ACCESS,
                         strictness=Strictness.MODERATE)],
    zones=[],
)

# Accept the negotiated terms
result = negotiator.accept(negotiation.id, "agent-alice")
print(result.status)  # NegotiationStatus.ACCEPTED
print(result.rounds)  # 2
```

## Architecture

| Module | Purpose |
|--------|---------|
| `boundary.py` | Boundary definitions with types, strictness levels, conditions, and exceptions |
| `zone.py` | Privacy zones (private/shared/public) with granular access rules |
| `access.py` | Permission grants, role-based access control, time-limited grants |
| `violations.py` | Violation detection, tracking, agent standing assessment |
| `negotiator.py` | Multi-round negotiation for shared boundaries between agents |

## License

MIT

---
<i>Built with [Cocapn](https://github.com/Lucineer/cocapn-ai).</i>

Superinstance & Lucineer (DiGennaro et al.)
