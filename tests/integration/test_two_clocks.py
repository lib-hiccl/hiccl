"""Integration tests for the Two Clocks example."""

import re
import time

# ---- Re-create the TwoClocks component here for isolated tests ----
import time as _time
from datetime import datetime, timezone

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
from hiccl.hiccup import div, h2, span
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions


class TwoClocks(Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_time = signal(_time.time() * 1000)

    @server
    def tick(self):
        self.server_time.set(_time.time() * 1000)

    def render(self):
        server_ms = self.server_time.get()
        server_dt = datetime.fromtimestamp(server_ms / 1000.0, tz=timezone.utc)
        server_str = server_dt.strftime("%H:%M:%S.") + str(
            server_dt.microsecond // 1000
        ).zfill(3)

        return div(
            {
                "class": "two-clocks",
                "hx-post": self.action_url("tick"),
                "hx-trigger": "every 1s",
                "hx-swap": "outerHTML",
                "data-server-ms": str(int(server_ms)),
            },
            h2("Two Clocks"),
            div(
                {"class": "clock-row"},
                "🖥  Server time: ",
                span({"class": "server-time"}, server_str),
            ),
            div(
                {"class": "clock-row"},
                "💻  Client time: ",
                span(
                    {
                        "class": "client-time",
                        "_": "init repeat forever ...",
                    },
                    "…",
                ),
            ),
            div(
                {"class": "clock-row"},
                "⏱  Skew: ",
                span(
                    {
                        "class": "skew",
                        "data-server-ms": str(int(server_ms)),
                        "_": "init repeat forever ...",
                    },
                    "…",
                ),
            ),
        )


# ---- Fixtures ----


@pytest.fixture
def clocks_app():
    registry = ComponentRegistry()
    registry.register("two-clocks", TwoClocks)

    config = HicclConfig(
        component_registry=registry,
        transport_modes={"http"},
    )
    app = create_hiccl_app(config)

    session = Session("clocks-session", registry, HiccupRenderer())
    comp = session.mount_component("two-clocks", cid="clocks-1")
    _sessions["clocks-session"] = session

    return app, comp


# ---- Unit tests ----


class TestTwoClocksUnit:
    def test_initial_server_time(self):
        comp = TwoClocks()
        comp._discovered_signals()
        ms = comp.server_time.get()
        assert ms > 0
        # Should be roughly current time
        assert abs(ms - time.time() * 1000) < 5000

    def test_tick_updates_time(self):
        comp = TwoClocks()
        comp._discovered_signals()
        old = comp.server_time.get()
        time.sleep(0.01)
        comp.tick()
        new = comp.server_time.get()
        assert new >= old

    def test_render_contains_server_time(self):
        comp = TwoClocks()
        comp._discovered_signals()
        tree = comp.render()
        # render() returns a div (not a fragment)
        r = HiccupRenderer()
        html = r.render(tree)
        assert "Server time:" in html
        assert "Client time:" in html
        assert "Skew:" in html
        assert "Two Clocks" in html

    def test_render_has_htmx_attrs_in_root_div(self):
        """htmx attrs are now in the root div returned by render()."""
        comp = TwoClocks()
        comp._discovered_signals()
        tree = comp.render()
        # tree is ["div", {"class": "two-clocks", "hx-post": ..., ...}, ...]
        assert tree[0] == "div"
        attrs = tree[1]
        assert isinstance(attrs, dict)
        assert "hx-post" in attrs
        assert "hx-trigger" in attrs
        assert "hx-swap" in attrs
        assert "data-server-ms" in attrs
        assert attrs["hx-trigger"] == "every 1s"
        assert attrs["hx-swap"] == "outerHTML"
        assert "tick" in attrs["hx-post"]
        assert "two-clocks" in attrs["class"]

    def test_render_htmx_attrs_update_with_signal(self):
        """data-server-ms in root div attrs changes after tick()."""
        comp = TwoClocks()
        comp._discovered_signals()
        ms1 = int(comp.render()[1]["data-server-ms"])
        time.sleep(0.01)
        comp.tick()
        ms2 = int(comp.render()[1]["data-server-ms"])
        assert ms2 >= ms1

    def test_render_component_has_htmx_attrs(self):
        """render_component injects id and htmx attrs appear in the same root div."""
        comp = TwoClocks()
        comp._discovered_signals()
        r = HiccupRenderer()
        html = r.render_component(comp)
        # The root div has id, class, and htmx attrs all together
        assert 'id="twoclocks-' in html or "twoclocks-" in html
        assert "hx-post" in html
        assert "hx-trigger" in html
        assert "data-server-ms" in html
        assert 'class="two-clocks"' in html


class TestTwoClocksHTTP:
    def test_initial_render(self, clocks_app):
        app, comp = clocks_app
        with TestClient(app) as client:
            r = HiccupRenderer()
            html = r.render_component(comp)
            assert "Server time:" in html
            assert "Client time:" in html
            assert "Two Clocks" in html
            # htmx attrs are in the same root div (no wrapper nesting)
            assert "hx-post" in html
            assert 'class="two-clocks"' in html

    def test_tick_action(self, clocks_app):
        app, comp = clocks_app
        with TestClient(app, cookies={"hiccl_sid": "clocks-session"}) as client:
            old_ms = comp.server_time.get()
            time.sleep(0.01)

            resp = client.post("/hiccl/action/clocks-1/tick")
            assert resp.status_code == 200
            assert comp.server_time.get() >= old_ms
            # Response HTML has htmx attrs on the root div
            assert "hx-post" in resp.text
            assert "data-server-ms" in resp.text

    def test_tick_updates_server_time_display(self, clocks_app):
        app, comp = clocks_app
        with TestClient(app, cookies={"hiccl_sid": "clocks-session"}) as client:
            resp1 = client.post("/hiccl/action/clocks-1/tick")
            html1 = resp1.text

            time.sleep(0.01)

            resp2 = client.post("/hiccl/action/clocks-1/tick")
            html2 = resp2.text

            # The two responses should have different data-server-ms values
            assert "data-server-ms" in html1
            assert "data-server-ms" in html2
            # ms values should differ (time has advanced)
            assert html1 != html2

    def test_tick_preserves_htmx_attrs(self, clocks_app):
        """After tick, the response must still contain htmx polling attrs."""
        app, comp = clocks_app
        with TestClient(app, cookies={"hiccl_sid": "clocks-session"}) as client:
            resp = client.post("/hiccl/action/clocks-1/tick")
            html = resp.text
            assert 'hx-trigger="every 1s"' in html
            assert 'hx-swap="outerHTML"' in html
            assert "tick" in html

    def test_tick_response_has_single_root_div(self, clocks_app):
        """The tick response is a single root div with id + htmx attrs (no wrapper)."""
        app, comp = clocks_app
        with TestClient(app, cookies={"hiccl_sid": "clocks-session"}) as client:
            resp = client.post("/hiccl/action/clocks-1/tick")
            html = resp.text.strip()
            # Should start with a div that has both id and class and htmx attrs
            assert html.startswith("<div")
            # The opening tag should contain id, class, hx-post, hx-trigger, hx-swap
            # Extract the opening tag
            opening = html[: html.index(">") + 1]
            assert 'class="two-clocks"' in opening
            assert "hx-post" in opening
            assert "hx-trigger" in opening
            assert "hx-swap" in opening
