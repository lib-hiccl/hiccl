"""Tests for hiccl.transport.sse — SSE handler."""

from hiccl.component import Component
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions


class TestSSETransport:
    def test_sse_invalid_session(self):
        """Verify SSE returns 404 for non-existent session."""
        from fastapi.testclient import TestClient

        from hiccl.app import HicclConfig, create_hiccl_app

        registry = ComponentRegistry()
        config = HicclConfig(
            component_registry=registry,
            transport_modes={"sse"},
        )
        app = create_hiccl_app(config)

        with TestClient(app) as client:
            resp = client.get("/hiccl/sse/invalid-session")
            assert resp.status_code == 404

    def test_sse_route_exists(self):
        """Verify the SSE route is registered."""
        from hiccl.app import HicclConfig, create_hiccl_app

        registry = ComponentRegistry()
        config = HicclConfig(
            component_registry=registry,
            transport_modes={"sse"},
        )
        app = create_hiccl_app(config)

        # Check that the SSE route exists in the app routes
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert any("/hiccl/sse/" in r for r in routes)
