"""Tests for hiccl.transport.http — HTTP action handler."""

import pytest
from fastapi.testclient import TestClient

from hiccl.component import Component, get_server_methods, server
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions
from hiccl.signal import Signal


class CounterComponent(Component):
    def __init__(self):
        super().__init__()
        self.count = Signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    def render(self):
        return ["div", None, f"Count: {self.count.get()}"]


@pytest.fixture
def setup_app():
    """Set up a FastAPI app with the HTTP transport for testing."""
    from hiccl.app import HicclConfig, create_hiccl_app

    registry = ComponentRegistry()
    registry.register("counter", CounterComponent)

    config = HicclConfig(
        component_registry=registry,
        transport_modes={"http"},
    )
    app = create_hiccl_app(config)

    # Create a session and mount a component
    session = Session("test-session-1", registry, HiccupRenderer())
    comp = session.mount_component("counter", cid="counter-1")
    _sessions["test-session-1"] = session

    return app, comp


class TestHTTPTransport:
    def test_action_increments_counter(self, setup_app):
        app, comp = setup_app
        with TestClient(app, cookies={"hiccl_sid": "test-session-1"}) as client:
            # Verify initial state
            assert comp.count.get() == 0

            # Trigger increment action
            resp = client.post(f"/hiccl/action/counter-1/increment")
            assert resp.status_code == 200
            assert comp.count.get() == 1
            assert "Count: 1" in resp.text

    def test_component_not_found(self, setup_app):
        app, _ = setup_app
        with TestClient(app, cookies={"hiccl_sid": "test-session-1"}) as client:
            resp = client.post("/hiccl/action/nonexistent/method")
            assert resp.status_code == 404

    def test_method_not_found(self, setup_app):
        app, _ = setup_app
        with TestClient(app, cookies={"hiccl_sid": "test-session-1"}) as client:
            resp = client.post("/hiccl/action/counter-1/nonexistent_method")
            assert resp.status_code == 404

    def test_session_not_found(self, setup_app):
        app, _ = setup_app
        with TestClient(app, cookies={"hiccl_sid": "invalid-session"}) as client:
            # With auto-session-creation, a new empty session is created
            # but the component won't exist in it
            resp = client.post("/hiccl/action/counter-1/increment")
            assert resp.status_code == 404  # Component not found in new session

    def test_render_after_increment(self, setup_app):
        app, comp = setup_app
        with TestClient(app, cookies={"hiccl_sid": "test-session-1"}) as client:
            # Increment twice
            client.post("/hiccl/action/counter-1/increment")
            resp = client.post("/hiccl/action/counter-1/increment")
            assert comp.count.get() == 2
            assert "Count: 2" in resp.text
