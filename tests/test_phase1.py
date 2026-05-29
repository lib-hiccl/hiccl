"""Automated test suite for Hiccl Phase 1 — HMR and hREPL functionalities."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
from fastapi import FastAPI
from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,
    create_hiccl_app,
    div,
    h1,
    p,
    signal,
)
from hiccl.repl.server import HReplServer


# ===========================================================================
# 1. HMR State-Preserving & Class-Swapping Tests
# ===========================================================================


class LegacyCounter(Component):
    """Old component definition before reload."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = signal(42)

    def render(self):
        return div(
            h1("Legacy Title"),
            p(f"Count is {self.count.get()}"),
        )


class UpdatedCounter(Component):
    """New component definition simulating after reload."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = signal(42)

    def render(self):
        return div(
            h1("Updated Title!"),
            p(f"Modern Count: {self.count.get()}"),
        )


@pytest.mark.asyncio
async def test_hmr_class_swapping_and_state_preservation():
    # 1. Set up Registry and App Config
    registry = ComponentRegistry()
    registry.register("counter", LegacyCounter)

    config = HicclConfig(
        component_registry=registry,
        pages={"/": LegacyCounter},
        live_reload=True,
    )
    app = create_hiccl_app(config)

    # Simulate start of lifespan to get local session store
    session_store = app.state.hiccl["session_store"]
    session = await session_store.get("test-session")
    if session is None:
        from hiccl.session import Session

        session = Session("test-session", registry, app.state.hiccl["renderer"])
        await session_store.save(session)

    # 2. Mount component and modify its live state
    comp = session.mount_component("counter", cid="counter-1")
    assert comp.count.get() == 42
    comp.count.set(100)  # Mutate state in memory
    assert comp.count.get() == 100

    # Verify initial render is legacy HTML
    html_legacy = session.renderer.render_component(comp)
    assert "Legacy Title" in html_legacy
    assert "Count is 100" in html_legacy

    # 3. Simulate HMR class swapping and registry updating
    # We update the registry map
    registry.register("counter", UpdatedCounter)

    # Update app configuration pages
    config.pages["/"] = UpdatedCounter

    # Perform active class replacement on the live instance
    comp.__class__ = UpdatedCounter

    # Clear cached rendered result of the component
    session.renderer._cache.pop("counter-1", None)

    # 4. Assert updated behavior while retaining the in-memory Signal state!
    assert comp.count.get() == 100  # Crucial: State preserved!

    html_updated = session.renderer.render_component(comp)
    assert "Updated Title!" in html_updated
    assert (
        "Modern Count: 100" in html_updated
    )  # State cleanly rendered by the new class!


# ===========================================================================
# 2. hREPL Socket Server & Evaluation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_hrepl_authentication_and_sandbox_evaluation():
    # Enable hREPL for the duration of this test
    os.environ["HREPL_ENABLED"] = "1"
    os.environ["HREPL_TOKEN"] = "test-secret-token"

    app = FastAPI()
    server = HReplServer(host="127.0.0.1", port=18998, app=app)
    await server.start()

    try:
        # Establish TCP connection
        reader, writer = await asyncio.open_connection("127.0.0.1", 18998)

        # 1. Send invalid token
        writer.write(json.dumps({"token": "wrong-token"}).encode("utf-8") + b"\n")
        await writer.drain()

        response_line = await reader.readline()
        resp = json.loads(response_line.decode("utf-8").strip())
        assert resp["status"] == "error"
        assert "Unauthorized" in resp["error"]

        writer.close()

        # 2. Connect again and send correct token
        reader, writer = await asyncio.open_connection("127.0.0.1", 18998)
        writer.write(json.dumps({"token": "test-secret-token"}).encode("utf-8") + b"\n")
        await writer.drain()

        response_line = await reader.readline()
        resp = json.loads(response_line.decode("utf-8").strip())
        assert resp["status"] == "ok"
        assert "Authenticated" in resp["message"]

        # 3. Evaluate basic math expression
        writer.write(json.dumps({"code": "1 + 1"}).encode("utf-8") + b"\n")
        await writer.drain()

        response_line = await reader.readline()
        resp = json.loads(response_line.decode("utf-8").strip())
        assert resp["status"] == "ok"
        assert resp["value"] == "2"

        # 4. Evaluate multi-line code statement & capture stdout prints!
        multi_line_code = "print('hello from hREPL')\nx = 100\nx * 2"
        writer.write(json.dumps({"code": multi_line_code}).encode("utf-8") + b"\n")
        await writer.drain()

        response_line = await reader.readline()
        resp = json.loads(response_line.decode("utf-8").strip())
        assert resp["status"] == "ok"
        assert resp["stdout"].strip() == "hello from hREPL"
        assert resp["value"] == "200"

        # 5. Evaluate async code with await keyword
        async_code = "import asyncio\nawait asyncio.sleep(0.01)\n'async ok'"
        writer.write(json.dumps({"code": async_code}).encode("utf-8") + b"\n")
        await writer.drain()

        response_line = await reader.readline()
        resp = json.loads(response_line.decode("utf-8").strip())
        assert resp["status"] == "ok"
        assert resp["value"] == "'async ok'"

        writer.close()

    finally:
        await server.stop()
        os.environ.pop("HREPL_ENABLED", None)
        os.environ.pop("HREPL_TOKEN", None)
