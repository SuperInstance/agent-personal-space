"""Tests for space negotiator."""

import time

from agent_personal_space.boundary import Boundary, BoundaryType, Strictness
from agent_personal_space.negotiator import (
    NegotiationResult,
    NegotiationStatus,
    NegotiationStrategy,
    SpaceNegotiator,
)
from agent_personal_space.zone import PersonalZone, ZoneType


def _make_boundary(owner: str, strictness: Strictness = Strictness.STRICT) -> Boundary:
    return Boundary(
        id=f"b-{owner}", owner_id=owner,
        boundary_type=BoundaryType.DATA_ACCESS, strictness=strictness,
    )


def _make_zone(owner: str, zone_type: ZoneType = ZoneType.SHARED) -> PersonalZone:
    return PersonalZone(id=f"z-{owner}", owner_id=owner, zone_type=zone_type)


class TestSpaceNegotiator:
    def test_propose(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        assert neg.status == NegotiationStatus.PROPOSED
        assert "a" in neg.participants
        assert "b" in neg.participants

    def test_counter(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        result = n.counter(neg.id, "b", [_make_boundary("b")], [_make_zone("b")])
        assert result is not None
        assert result.status == NegotiationStatus.COUNTERED
        assert len(result.proposals) == 2

    def test_accept(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        result = n.accept(neg.id, "b")
        assert result is not None
        assert result.status == NegotiationStatus.ACCEPTED
        assert result.completed_at is not None

    def test_reject(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        result = n.reject(neg.id, "b", "not acceptable")
        assert result is not None
        assert result.status == NegotiationStatus.REJECTED
        assert result.notes == "not acceptable"

    def test_counter_then_accept(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        n.counter(neg.id, "b", [_make_boundary("b")], [_make_zone("b")])
        result = n.accept(neg.id, "a")
        assert result is not None
        assert result.rounds == 2

    def test_max_rounds(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        neg.max_rounds = 2
        n.counter(neg.id, "b", [_make_boundary("b")], [_make_zone("b")])
        result = n.counter(neg.id, "a", [_make_boundary("a")], [_make_zone("a")])
        assert result is not None
        assert result.status == NegotiationStatus.EXPIRED

    def test_accept_nonexistent(self):
        n = SpaceNegotiator()
        assert n.accept("fake", "a") is None

    def test_reject_non_participant(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        assert n.reject(neg.id, "c") is None

    def test_list_active(self):
        n = SpaceNegotiator()
        n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        n.propose("c", "d", [_make_boundary("c")], [_make_zone("c")])
        active = n.list_active()
        assert len(active) == 2
        active_a = n.list_active(agent_id="a")
        assert len(active_a) == 1

    def test_get_negotiation(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        assert n.get_negotiation(neg.id) is not None
        assert n.get_negotiation("fake") is None

    def test_get_result(self):
        n = SpaceNegotiator()
        neg = n.propose("a", "b", [_make_boundary("a")], [_make_zone("a")])
        n.accept(neg.id, "b")
        result = n.get_result(neg.id)
        assert result is not None

    def test_cooperative_strategy_merges(self):
        n = SpaceNegotiator()
        b1 = _make_boundary("a", Strictness.ADVISORY)
        b2 = _make_boundary("a", Strictness.ABSOLUTE)
        neg = n.propose("a", "b", [b1], [_make_zone("a")], strategy=NegotiationStrategy.COOPERATIVE)
        n.counter(neg.id, "b", [b2], [_make_zone("b")])
        result = n.accept(neg.id, "a")
        assert result is not None
        # Cooperative keeps strictest
        assert any(b.strictness == Strictness.ABSOLUTE for b in result.agreed_boundaries)

    def test_compromise_strategy(self):
        n = SpaceNegotiator()
        b1 = _make_boundary("a", Strictness.ABSOLUTE)
        neg = n.propose("a", "b", [b1], [_make_zone("a")], strategy=NegotiationStrategy.COMPROMISE)
        n.counter(neg.id, "b", [_make_boundary("a", Strictness.STRICT)], [_make_zone("b")])
        result = n.accept(neg.id, "a")
        assert result is not None
        # Compromise resolves to MODERATE
        assert all(b.strictness == Strictness.MODERATE for b in result.agreed_boundaries)

    def test_assertive_uses_last(self):
        n = SpaceNegotiator()
        b1 = _make_boundary("a", Strictness.ADVISORY)
        b2 = _make_boundary("b", Strictness.ABSOLUTE)
        neg = n.propose("a", "b", [b1], [_make_zone("a")], strategy=NegotiationStrategy.ASSERTIVE)
        n.counter(neg.id, "b", [b2], [_make_zone("b")])
        result = n.accept(neg.id, "a")
        assert result is not None
        # Assertive uses last proposal
        assert len(result.agreed_boundaries) == 1
        assert result.agreed_boundaries[0].owner_id == "b"

    def test_deferential_uses_first(self):
        n = SpaceNegotiator()
        b1 = _make_boundary("a", Strictness.ADVISORY)
        b2 = _make_boundary("b", Strictness.ABSOLUTE)
        neg = n.propose("a", "b", [b1], [_make_zone("a")], strategy=NegotiationStrategy.DEFERENTIAL)
        n.counter(neg.id, "b", [b2], [_make_zone("b")])
        result = n.accept(neg.id, "a")
        assert result is not None
        assert len(result.agreed_boundaries) == 1
        assert result.agreed_boundaries[0].owner_id == "a"
