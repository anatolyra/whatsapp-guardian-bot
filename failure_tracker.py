class FailureTracker:
    """In-memory failure counter with configurable notification logic."""

    def __init__(self, notify_first: bool = True, notify_interval: int = 3):
        """
        Initialize the failure tracker.

        Args:
            notify_first: If True, send notification on first failure
            notify_interval: Send notification every N failures after first (0 = disabled)
        """
        self._count = 0
        self._notify_first = notify_first
        self._notify_interval = notify_interval

    def record_failure(self) -> int:
        """Increment failure count and return new count."""
        self._count += 1
        return self._count

    def record_success(self) -> None:
        """Reset failure count."""
        self._count = 0

    def should_notify(self) -> bool:
        """Check if a notification should be sent based on current failure count."""
        if self._count == 0:
            return False
        if self._notify_first and self._count == 1:
            return True
        if self._notify_interval > 0 and self._count % self._notify_interval == 0:
            return True
        return False

    def get_count(self) -> int:
        """Return current failure count."""
        return self._count
