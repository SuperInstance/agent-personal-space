"""Tests for boundary module."""

import time

from agent_personal_space.boundary import Boundary, BoundaryType, Strictness


class TestBoundary:
    def test_create(self):
        b = Boundary(id="b1", owner_id="agent-a", boundary_type=BoundaryType.DATA_ACCESS, strictness=Strictness.STRICT)
        assert b.id == "b1"
        assert b.owner_id == "agent-a"
        assert not b.is_expired()

    def test_expired(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.COMMUNICATION,
            strictness=Strictness.MODERATE, expires_at=time.time() - 100,
        )
        assert b.is_expired()

    def test_not_expired(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.COMMUNICATION,
            strictness=Strictness.MODERATE, expires_at=time.time() + 3600,
        )
        assert not b.is_expired()

    def test_owner_always_allowed(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.RESOURCE, strictness=Strictness.ABSOLUTE)
        result = b.evaluate("a")
        assert result.allowed

    def test_exempted_agent(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.RESOURCE, strictness=Strictness.STRICT, exceptions=["b"])
        result = b.evaluate("b")
        assert result.allowed
        assert "exempted" in result.reason

    def test_strict_blocks(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.DATA_ACCESS, strictness=Strictness.STRICT)
        result = b.evaluate("c")
        assert not result.allowed

    def test_absolute_blocks(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.DATA_ACCESS, strictness=Strictness.ABSOLUTE)
        result = b.evaluate("c")
        assert not result.allowed

    def test_advisory_allows(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.BEHAVIORAL, strictness=Strictness.ADVISORY)
        result = b.evaluate("c")
        assert result.allowed

    def test_moderate_blocks(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.COMMUNICATION, strictness=Strictness.MODERATE)
        result = b.evaluate("c")
        assert not result.allowed

    def test_conditions_exact_match(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.TEMPORAL,
            strictness=Strictness.STRICT, conditions={"mode": "production"},
        )
        assert b.check_conditions({"mode": "production"})
        assert not b.check_conditions({"mode": "development"})

    def test_conditions_callable(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.TEMPORAL,
            strictness=Strictness.STRICT, conditions={"level": lambda x: x > 5},
        )
        assert b.check_conditions({"level": 10})
        assert not b.check_conditions({"level": 3})

    def test_conditions_not_met_means_allowed(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.DATA_ACCESS,
            strictness=Strictness.STRICT, conditions={"env": "prod"},
        )
        result = b.evaluate("c", context={"env": "dev"})
        assert result.allowed  # conditions not met → boundary doesn't apply

    def test_expired_boundary_allows(self):
        b = Boundary(
            id="b1", owner_id="a", boundary_type=BoundaryType.RESOURCE,
            strictness=Strictness.ABSOLUTE, expires_at=time.time() - 1,
        )
        result = b.evaluate("c")
        assert result.allowed
        assert "expired" in result.reason

    def test_add_remove_exception(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.RESOURCE, strictness=Strictness.STRICT)
        b.add_exception("c")
        assert b.is_agent_exempted("c")
        b.remove_exception("c")
        assert not b.is_agent_exempted("c")

    def test_add_duplicate_exception(self):
        b = Boundary(id="b1", owner_id="a", boundary_type=BoundaryType.RESOURCE, strictness=Strictness.STRICT)
        b.add_exception("c")
        b.add_exception("c")
        assert b.exceptions.count("c") == 1
