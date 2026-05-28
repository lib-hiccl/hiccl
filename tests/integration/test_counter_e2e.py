"""Integration test — Counter HTTP cycle end-to-end."""

import pytest
from fastapi.testclient import TestClient

from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,
    create_hiccl_app,
    server,
    signal,
)
from hiccl.hiccup import button, div, h2
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions


class Counter(Component):
    def __init__(self):
        super().__init__()
        self.count = signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    @server
    def decrement(self):
        self.count.set(self.count.get() - 1)

    @server
    def reset(self):
        self.count.set(0)

    def render(self):
        count = self.count.get()
        return div(
            {"class": "counter"},
            h2(f"Count: {count}"),
            button({"hx-post": self.action_url("decrement")}, "-1"),
            button({"hx-post": self.action_url("reset")}, "Reset"),
            button({"hx-post": self.action_url("increment")}, "+1"),
        )


@pytest.fixture
def counter_app():
    registry = ComponentRegistry()
    registry.register("counter", Counter)

    config = HicclConfig(
        component_registry=registry,
        transport_modes={"http"},
    )
    app = create_hiccl_app(config)

    # Set up session
    session = Session("integration-session", registry, HiccupRenderer())
    comp = session.mount_component("counter", cid="counter-1")
    _sessions["integration-session"] = session

    return app, comp


class TestCounterHTTPCycle:
    def test_initial_render(self, counter_app):
        app, comp = counter_app
        with TestClient(app) as client:
            html = HiccupRenderer().render_component(comp)
            assert "Count: 0" in html

    def test_increment_action(self, counter_app):
        app, comp = counter_app
        with TestClient(app, cookies={"hiccl_sid": "integration-session"}) as client:
            resp = client.post("/hiccl/action/counter-1/increment")
            assert resp.status_code == 200
            assert "Count: 1" in resp.text
            assert comp.count.get() == 1

    def test_decrement_action(self, counter_app):
        app, comp = counter_app
        with TestClient(app, cookies={"hiccl_sid": "integration-session"}) as client:
            resp = client.post("/hiccl/action/counter-1/decrement")
            assert resp.status_code == 200
            assert "Count: -1" in resp.text
            assert comp.count.get() == -1

    def test_reset_action(self, counter_app):
        app, comp = counter_app
        with TestClient(app, cookies={"hiccl_sid": "integration-session"}) as client:
            # Increment first
            comp.increment()
            comp.increment()
            assert comp.count.get() == 2

            # Then reset
            resp = client.post("/hiccl/action/counter-1/reset")
            assert resp.status_code == 200
            assert "Count: 0" in resp.text
            assert comp.count.get() == 0

    def test_full_cycle(self, counter_app):
        app, comp = counter_app
        with TestClient(app, cookies={"hiccl_sid": "integration-session"}) as client:
            # Increment 3 times
            for _ in range(3):
                client.post("/hiccl/action/counter-1/increment")
            assert comp.count.get() == 3

            # Decrement once
            client.post("/hiccl/action/counter-1/decrement")
            assert comp.count.get() == 2

            # Reset
            resp = client.post("/hiccl/action/counter-1/reset")
            assert resp.status_code == 200
            assert "Count: 0" in resp.text
            assert comp.count.get() == 0

    def test_action_url_format(self):
        comp = Counter()
        url = comp.action_url("increment")
        assert url.startswith("/hiccl/action/")
        assert "increment" in url
