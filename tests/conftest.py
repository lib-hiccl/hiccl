"""Global pytest configuration and fixtures for Hiccl tests."""

import pytest

from hiccl.session import _sessions


@pytest.fixture(autouse=True)
def cleanup_global_sessions():
    """Ensure each test runs with a completely clean and isolated session pool."""
    yield
    # Dispose all sessions to clean up effects, EventBus queues, and timers
    for session in list(_sessions.values()):
        try:
            session.dispose()
        except Exception:
            pass
    _sessions.clear()
