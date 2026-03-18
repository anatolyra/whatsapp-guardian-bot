import pytest
from failure_tracker import FailureTracker

def test_initial_count_is_zero():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    assert tracker.get_count() == 0

def test_record_failure_increments():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    count = tracker.record_failure()
    assert count == 1
    assert tracker.get_count() == 1

def test_record_success_resets():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    assert tracker.get_count() == 0

def test_should_notify_first_failure():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    tracker.record_failure()
    assert tracker.should_notify() is True

def test_should_notify_second_failure():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    tracker.record_failure()  # count=1, should notify
    tracker.record_failure()  # count=2, should NOT notify
    assert tracker.should_notify() is False

def test_should_notify_third_failure():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    tracker.record_failure()  # count=1
    tracker.record_failure()  # count=2
    tracker.record_failure()  # count=3, should notify
    assert tracker.should_notify() is True

def test_should_notify_interval_zero():
    tracker = FailureTracker(notify_first=True, notify_interval=0)
    tracker.record_failure()  # count=1, should notify (first)
    assert tracker.should_notify() is True
    tracker.record_failure()  # count=2
    assert tracker.should_notify() is False
    tracker.record_failure()  # count=3
    assert tracker.should_notify() is False

def test_should_notify_first_disabled():
    tracker = FailureTracker(notify_first=False, notify_interval=3)
    tracker.record_failure()  # count=1, should NOT notify (first disabled)
    assert tracker.should_notify() is False
    tracker.record_failure()  # count=2
    tracker.record_failure()  # count=3, should notify (interval)
    assert tracker.should_notify() is True

def test_should_notify_after_success_reset():
    tracker = FailureTracker(notify_first=True, notify_interval=3)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    tracker.record_failure()  # count=1 again, should notify
    assert tracker.should_notify() is True
