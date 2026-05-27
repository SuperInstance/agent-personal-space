"""Tests for violation tracker."""

import time

from agent_personal_space.violations import ViolationSeverity, ViolationTracker


class TestViolationTracker:
    def test_record(self):
        tracker = ViolationTracker()
        v = tracker.record("a", "b1", ViolationSeverity.MEDIUM, "bad behavior")
        assert v.violator_id == "a"
        assert v.boundary_id == "b1"
        assert not v.resolved

    def test_get_violations_filter(self):
        tracker = ViolationTracker()
        tracker.record("a", "b1", ViolationSeverity.LOW)
        tracker.record("a", "b2", ViolationSeverity.HIGH)
        tracker.record("b", "b1", ViolationSeverity.MEDIUM)

        assert len(tracker.get_violations(violator_id="a")) == 2
        assert len(tracker.get_violations(boundary_id="b1")) == 2
        assert len(tracker.get_violations(severity=ViolationSeverity.HIGH)) == 1

    def test_resolve(self):
        tracker = ViolationTracker()
        v = tracker.record("a", "b1", ViolationSeverity.MEDIUM)
        result = tracker.resolve_violation(v.id, "fixed")
        assert result is not None
        assert result.resolved
        assert result.resolution_note == "fixed"

    def test_resolve_nonexistent(self):
        tracker = ViolationTracker()
        assert tracker.resolve_violation("999") is None

    def test_filter_resolved(self):
        tracker = ViolationTracker()
        v = tracker.record("a", "b1", ViolationSeverity.LOW)
        tracker.record("a", "b2", ViolationSeverity.LOW)
        tracker.resolve_violation(v.id)
        assert len(tracker.get_violations(resolved=True)) == 1
        assert len(tracker.get_violations(resolved=False)) == 1

    def test_agent_standing_clean(self):
        tracker = ViolationTracker()
        standing = tracker.get_agent_standing("a")
        assert standing.status == "clean"
        assert standing.total_violations == 0

    def test_agent_standing_warning(self):
        tracker = ViolationTracker()
        tracker.record("a", "b1", ViolationSeverity.LOW)
        standing = tracker.get_agent_standing("a")
        assert standing.status == "warning"

    def test_agent_standing_restricted(self):
        tracker = ViolationTracker()
        tracker.record("a", "b1", ViolationSeverity.MEDIUM)
        tracker.record("a", "b2", ViolationSeverity.MEDIUM)
        standing = tracker.get_agent_standing("a")
        assert standing.status in ("warning", "restricted", "banned")

    def test_agent_standing_banned(self):
        tracker = ViolationTracker()
        for i in range(3):
            tracker.record("a", f"b{i}", ViolationSeverity.HIGH)
        standing = tracker.get_agent_standing("a")
        assert standing.status in ("restricted", "banned")

    def test_standing_improves_after_resolve(self):
        tracker = ViolationTracker()
        v = tracker.record("a", "b1", ViolationSeverity.MEDIUM)
        tracker.resolve_violation(v.id)
        standing = tracker.get_agent_standing("a")
        assert standing.status == "clean"

    def test_summary(self):
        tracker = ViolationTracker()
        tracker.record("a", "b1", ViolationSeverity.LOW)
        tracker.record("b", "b2", ViolationSeverity.HIGH)
        summary = tracker.summary()
        assert summary.total == 2
        assert summary.unique_violators == 2

    def test_max_violations(self):
        tracker = ViolationTracker(max_violations=5)
        for i in range(10):
            tracker.record("a", f"b{i}", ViolationSeverity.LOW)
        assert len(tracker.get_violations()) == 5

    def test_filter_by_since(self):
        tracker = ViolationTracker()
        tracker.record("a", "b1", ViolationSeverity.LOW)
        cutoff = time.time() + 0.01
        time.sleep(0.02)
        tracker.record("a", "b2", ViolationSeverity.LOW)
        assert len(tracker.get_violations(since=cutoff)) == 1
