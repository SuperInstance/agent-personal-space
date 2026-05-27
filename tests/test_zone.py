"""Tests for zone module."""

import time

from agent_personal_space.zone import PersonalZone, ZoneAccessRule, ZoneType


class TestZoneAccessRule:
    def test_matches_agent_specific(self):
        rule = ZoneAccessRule(agent_id="a", permissions={"read", "write"})
        assert rule.matches_agent("a")
        assert not rule.matches_agent("b")

    def test_matches_agent_wildcard(self):
        rule = ZoneAccessRule(agent_id=None, permissions={"read"})
        assert rule.matches_agent("anyone")

    def test_expired(self):
        rule = ZoneAccessRule(agent_id="a", permissions={"read"}, expires_at=time.time() - 1)
        assert rule.is_expired()

    def test_has_permission(self):
        rule = ZoneAccessRule(agent_id="a", permissions={"read", "write"})
        assert rule.has_permission("read")
        assert not rule.has_permission("delete")


class TestPersonalZone:
    def _make_zone(self, zone_type: ZoneType = ZoneType.SHARED) -> PersonalZone:
        return PersonalZone(id="z1", owner_id="owner", zone_type=zone_type, name="Test Zone")

    def test_owner_always_has_access(self):
        zone = self._make_zone(ZoneType.PRIVATE)
        result = zone.check_access("owner", "read")
        assert result.allowed

    def test_private_zone_blocks_others(self):
        zone = self._make_zone(ZoneType.PRIVATE)
        result = zone.check_access("other", "read")
        assert not result.allowed
        assert "Private" in result.reason

    def test_public_zone_allows_by_default(self):
        zone = self._make_zone(ZoneType.PUBLIC)
        result = zone.check_access("other", "read")
        assert result.allowed

    def test_shared_zone_blocks_without_rules(self):
        zone = self._make_zone(ZoneType.SHARED)
        result = zone.check_access("other", "read")
        assert not result.allowed

    def test_grant_and_check_access(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read", "write"})
        result = zone.check_access("other", "read")
        assert result.allowed

    def test_grant_missing_permission(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read"})
        result = zone.check_access("other", "delete")
        assert not result.allowed

    def test_revoke_all(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read", "write"})
        removed = zone.revoke_access("other")
        assert removed == 2
        assert zone.check_access("other", "read").allowed is False

    def test_revoke_specific(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read", "write"})
        removed = zone.revoke_access("other", {"write"})
        assert removed == 1
        assert zone.check_access("other", "read").allowed
        assert not zone.check_access("other", "write").allowed

    def test_expired_grant(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read"}, expires_at=time.time() - 1)
        result = zone.check_access("other", "read")
        assert not result.allowed

    def test_list_agents(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("a", {"read"})
        zone.grant_access("b", {"read"})
        assert zone.list_agents_with_access() == {"a", "b"}

    def test_grant_extends_existing(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read"})
        zone.grant_access("other", {"write"})
        assert len([r for r in zone.access_rules if r.agent_id == "other"]) == 1
        assert zone.check_access("other", "read").allowed
        assert zone.check_access("other", "write").allowed

    def test_remove_specific_permission(self):
        zone = self._make_zone(ZoneType.SHARED)
        zone.grant_access("other", {"read", "write", "execute"})
        zone.remove_access_rule("other", "write")
        assert zone.check_access("other", "read").allowed
        assert not zone.check_access("other", "write").allowed
        assert zone.check_access("other", "execute").allowed
