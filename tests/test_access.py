"""Tests for access control module."""

import time

from agent_personal_space.access import AccessControl, Permission, Role


class TestRoles:
    def test_owner_has_all(self):
        assert Role.OWNER.default_permissions == set(Permission)

    def test_viewer_has_read_only(self):
        assert Role.VIEWER.default_permissions == {Permission.READ}

    def test_guest_has_read_only(self):
        assert Role.GUEST.default_permissions == {Permission.READ}

    def test_collaborator_permissions(self):
        assert Role.COLLABORATOR.default_permissions == {Permission.READ, Permission.WRITE, Permission.EXECUTE}


class TestAccessControl:
    def test_grant_and_check(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ, Permission.WRITE})
        assert ac.check("b", Permission.READ).allowed
        assert ac.check("b", Permission.WRITE).allowed
        assert not ac.check("b", Permission.DELETE).allowed

    def test_grant_different_resource(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ}, resource="res-1")
        assert ac.check("b", Permission.READ, resource="res-1").allowed
        assert not ac.check("b", Permission.READ, resource="res-2").allowed

    def test_wildcard_resource(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ}, resource="*")
        assert ac.check("b", Permission.READ, resource="anything").allowed

    def test_expired_grant(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ}, expires_at=time.time() - 1)
        assert not ac.check("b", Permission.READ).allowed

    def test_revoke(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ})
        ac.revoke("a", "b")
        assert not ac.check("b", Permission.READ).allowed

    def test_role_based_access(self):
        ac = AccessControl()
        ac.assign_role("b", Role.COLLABORATOR)
        assert ac.check("b", Permission.READ).allowed
        assert ac.check("b", Permission.WRITE).allowed
        assert not ac.check("b", Permission.ADMIN).allowed

    def test_expired_role(self):
        ac = AccessControl()
        ac.assign_role("b", Role.VIEWER, expires_at=time.time() - 1)
        assert not ac.check("b", Permission.READ).allowed

    def test_get_agent_permissions(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ})
        ac.assign_role("b", Role.COLLABORATOR)
        perms = ac.get_agent_permissions("b")
        assert Permission.READ in perms
        assert Permission.WRITE in perms
        assert Permission.EXECUTE in perms

    def test_list_grants(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ})
        ac.grant("a", "c", {Permission.WRITE})
        assert len(ac.list_grants()) == 2
        assert len(ac.list_grants("b")) == 1

    def test_cleanup(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ}, expires_at=time.time() - 1)
        ac.grant("a", "c", {Permission.READ})
        removed = ac.cleanup_expired()
        assert removed >= 1
        assert len(ac.list_grants()) == 1

    def test_grant_overrides_revocation(self):
        ac = AccessControl()
        ac.grant("a", "b", {Permission.READ})
        ac.revoke("a", "b")
        ac.grant("a", "b", {Permission.READ})
        assert ac.check("b", Permission.READ).allowed
