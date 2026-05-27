"""Space negotiation between agents."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_personal_space.boundary import Boundary, BoundaryType, Strictness
from agent_personal_space.zone import PersonalZone, ZoneType


class NegotiationStatus(Enum):
    """Status of a negotiation."""
    PROPOSED = "proposed"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class NegotiationStrategy(Enum):
    """Strategy for negotiation."""
    COOPERATIVE = "cooperative"   # Seeks win-win
    COMPROMISE = "compromise"     # Meets in the middle
    ASSERTIVE = "assertive"       # Favors own boundaries
    DEFERENTIAL = "deferential"   # Favors other's boundaries


@dataclass
class NegotiationProposal:
    """A proposal in a negotiation."""
    proposer_id: str
    target_id: str
    proposed_boundaries: list[Boundary]
    proposed_zones: list[PersonalZone]
    message: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


@dataclass
class NegotiationResult:
    """Result of a completed negotiation."""
    negotiation_id: str
    participants: list[str]
    status: NegotiationStatus
    agreed_boundaries: list[Boundary]
    agreed_zones: list[PersonalZone]
    rounds: int
    started_at: float
    completed_at: float | None = None
    notes: str = ""


@dataclass
class Negotiation:
    """An active negotiation session between agents."""
    id: str
    participants: list[str]
    proposals: list[NegotiationProposal] = field(default_factory=list)
    status: NegotiationStatus = NegotiationStatus.PROPOSED
    strategy: NegotiationStrategy = NegotiationStrategy.COOPERATIVE
    max_rounds: int = 10
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class SpaceNegotiator:
    """Facilitates negotiation of shared boundaries between agents.

    Agents can propose, counter, accept, or reject boundary configurations.
    The negotiator applies strategies to find mutually acceptable terms.
    """

    def __init__(self) -> None:
        self._negotiations: dict[str, Negotiation] = {}
        self._results: dict[str, NegotiationResult] = {}
        self._next_id = 1

    def propose(
        self,
        proposer_id: str,
        target_id: str,
        boundaries: list[Boundary],
        zones: list[PersonalZone],
        message: str = "",
        strategy: NegotiationStrategy = NegotiationStrategy.COOPERATIVE,
        expires_at: float | None = None,
    ) -> Negotiation:
        """Create a new negotiation proposal."""
        negotiation = Negotiation(
            id=str(self._next_id),
            participants=[proposer_id, target_id],
            strategy=strategy,
        )
        self._next_id += 1

        proposal = NegotiationProposal(
            proposer_id=proposer_id,
            target_id=target_id,
            proposed_boundaries=boundaries,
            proposed_zones=zones,
            message=message,
            expires_at=expires_at,
        )
        negotiation.proposals.append(proposal)
        self._negotiations[negotiation.id] = negotiation
        return negotiation

    def counter(
        self,
        negotiation_id: str,
        counterer_id: str,
        boundaries: list[Boundary],
        zones: list[PersonalZone],
        message: str = "",
    ) -> Negotiation | None:
        """Submit a counter-proposal to an existing negotiation."""
        negotiation = self._negotiations.get(negotiation_id)
        if negotiation is None:
            return None
        if negotiation.status != NegotiationStatus.PROPOSED and negotiation.status != NegotiationStatus.COUNTERED:
            return None
        if len(negotiation.proposals) >= negotiation.max_rounds:
            negotiation.status = NegotiationStatus.EXPIRED
            return negotiation

        proposal = NegotiationProposal(
            proposer_id=counterer_id,
            target_id=negotiation.participants[0] if counterer_id == negotiation.participants[1] else negotiation.participants[1],
            proposed_boundaries=boundaries,
            proposed_zones=zones,
            message=message,
        )
        negotiation.proposals.append(proposal)
        negotiation.status = NegotiationStatus.COUNTERED
        negotiation.updated_at = time.time()
        return negotiation

    def accept(self, negotiation_id: str, accepter_id: str) -> NegotiationResult | None:
        """Accept the latest proposal in a negotiation."""
        negotiation = self._negotiations.get(negotiation_id)
        if negotiation is None:
            return None
        if accepter_id not in negotiation.participants:
            return None
        if not negotiation.proposals:
            return None

        latest = negotiation.proposals[-1]
        negotiation.status = NegotiationStatus.ACCEPTED
        negotiation.updated_at = time.time()

        # Merge boundaries using the negotiation strategy
        merged = self._merge_boundaries(negotiation)

        result = NegotiationResult(
            negotiation_id=negotiation.id,
            participants=negotiation.participants,
            status=NegotiationStatus.ACCEPTED,
            agreed_boundaries=merged.boundaries,
            agreed_zones=merged.zones,
            rounds=len(negotiation.proposals),
            started_at=negotiation.created_at,
            completed_at=time.time(),
        )
        self._results[negotiation.id] = result
        return result

    def reject(self, negotiation_id: str, rejecter_id: str, reason: str = "") -> NegotiationResult | None:
        """Reject the negotiation."""
        negotiation = self._negotiations.get(negotiation_id)
        if negotiation is None:
            return None
        if rejecter_id not in negotiation.participants:
            return None

        negotiation.status = NegotiationStatus.REJECTED
        negotiation.updated_at = time.time()

        result = NegotiationResult(
            negotiation_id=negotiation.id,
            participants=negotiation.participants,
            status=NegotiationStatus.REJECTED,
            agreed_boundaries=[],
            agreed_zones=[],
            rounds=len(negotiation.proposals),
            started_at=negotiation.created_at,
            completed_at=time.time(),
            notes=reason,
        )
        self._results[negotiation.id] = result
        return result

    def get_negotiation(self, negotiation_id: str) -> Negotiation | None:
        """Get a negotiation by ID."""
        return self._negotiations.get(negotiation_id)

    def get_result(self, negotiation_id: str) -> NegotiationResult | None:
        """Get a negotiation result by ID."""
        return self._results.get(negotiation_id)

    def list_active(self, agent_id: str | None = None) -> list[Negotiation]:
        """List active negotiations, optionally filtered by participant."""
        results = []
        for n in self._negotiations.values():
            if n.status in (NegotiationStatus.PROPOSED, NegotiationStatus.COUNTERED):
                if agent_id is None or agent_id in n.participants:
                    results.append(n)
        return results

    def _merge_boundaries(self, negotiation: Negotiation) -> MergedResult:
        """Merge proposals based on negotiation strategy."""
        if not negotiation.proposals:
            return MergedResult(boundaries=[], zones=[])

        all_boundaries: list[Boundary] = []
        all_zones: list[PersonalZone] = []

        for proposal in negotiation.proposals:
            all_boundaries.extend(proposal.proposed_boundaries)
            all_zones.extend(proposal.proposed_zones)

        # Strategy-based merging
        if negotiation.strategy == NegotiationStrategy.ASSERTIVE:
            # Use the most recent proposal (last counter)
            latest = negotiation.proposals[-1]
            return MergedResult(
                boundaries=latest.proposed_boundaries,
                zones=latest.proposed_zones,
            )
        elif negotiation.strategy == NegotiationStrategy.DEFERENTIAL:
            # Use the first proposal
            first = negotiation.proposals[0]
            return MergedResult(
                boundaries=first.proposed_boundaries,
                zones=first.proposed_zones,
            )
        else:
            # COOPERATIVE / COMPROMISE: use strictest boundaries, merge zones
            merged_boundaries = self._resolve_boundaries(all_boundaries, negotiation.strategy)
            merged_zones = self._resolve_zones(all_zones)
            return MergedResult(boundaries=merged_boundaries, zones=merged_zones)

    @staticmethod
    def _resolve_boundaries(boundaries: list[Boundary], strategy: NegotiationStrategy) -> list[Boundary]:
        """Resolve overlapping boundaries by keeping the strictest."""
        by_type: dict[tuple[str, BoundaryType], Boundary] = {}
        for b in boundaries:
            key = (b.owner_id, b.boundary_type)
            if key not in by_type:
                by_type[key] = b
            else:
                existing = by_type[key]
                strictness_order = {
                    Strictness.ADVISORY: 0,
                    Strictness.MODERATE: 1,
                    Strictness.STRICT: 2,
                    Strictness.ABSOLUTE: 3,
                }
                if strategy == NegotiationStrategy.COMPROMISE:
                    # Pick moderate strictness
                    target = Strictness.MODERATE
                    b2 = b
                    b2.strictness = target
                    by_type[key] = b2
                elif strictness_order[b.strictness] > strictness_order[existing.strictness]:
                    by_type[key] = b
        return list(by_type.values())

    @staticmethod
    def _resolve_zones(zones: list[PersonalZone]) -> list[PersonalZone]:
        """Deduplicate zones by ID."""
        seen: dict[str, PersonalZone] = {}
        for z in zones:
            if z.id not in seen:
                seen[z.id] = z
        return list(seen.values())


@dataclass
class MergedResult:
    """Internal helper for merged negotiation results."""
    boundaries: list[Boundary]
    zones: list[PersonalZone]
