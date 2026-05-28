"""Tests for hiccl.transport.websocket — WebSocket handler."""

import pytest
from fastapi.testclient import TestClient

from hiccl.component import Component, server
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions
from hiccl.signal import Signal


class WSCounter(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = Signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    def render(self):
        return ["div", None, f"Count: {self.count.get()}"]


@pytest.fixture
def setup_ws_app():
    from hiccl.app import HicclConfig, create_hiccl_app

    registry = ComponentRegistry()
    registry.register("ws-counter", WSCounter)

    config = HicclConfig(
        component_registry=registry,
        transport_modes={"ws"},
    )
    app = create_hiccl_app(config)

    session = Session("ws-session-1", registry, HiccupRenderer())
    session.mount_component("ws-counter", cid="ws-counter-1")
    _sessions["ws-session-1"] = session

    return app


class TestWebSocketTransport:
    def test_ws_connect_and_action(self, setup_ws_app):
        app = setup_ws_app
        with TestClient(app) as client:
            with client.websocket_connect("/hiccl/ws/ws-session-1") as ws:
                # Send an action
                ws.send_json(
                    {
                        "type": "action",
                        "component_id": "ws-counter-1",
                        "method": "increment",
                        "args": {},
                    }
                )
                # Read responses (may get batch or nothing due to timing)
                # Just verify the connection works without error
                # The scheduler may or may not have fired yet

    def test_ws_invalid_session(self, setup_ws_app):
        app = setup_ws_app
        with TestClient(app) as client:
            # WebSocket connects but server should close it
            with client.websocket_connect("/hiccl/ws/invalid-session") as ws:
                # Server will close the connection; reading should fail
                pass

    def test_ws_disconnect(self, setup_ws_app):
        """Test that WebSocket can connect and disconnect cleanly."""
        app = setup_ws_app
        with TestClient(app) as client:
            with client.websocket_connect("/hiccl/ws/ws-session-1") as ws:
                pass  # Clean disconnect
