"""Two Clocks — server time via SSE/WS push, client time via hyperscript.

Demonstrates:
  - No hx-trigger polling — server pushes updates via real-time transport
  - ActionRef as hx-post value with explicit hx-trigger override
  - Hyperscript for client-side time
"""

import time
from datetime import datetime, timezone

from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,
    create_hiccl_app,
    menu,
    server,
    signal,
)
from hiccl.hiccup import div, h2, span


class ServerTimeDisplay(Component):
    """Sub-component that displays the server time and handles its high-frequency reactive updates."""

    def __init__(self, **kwargs):
        self.server_time = kwargs.pop("server_time", None)
        super().__init__(**kwargs)

    def render(self):
        server_ms = self.server_time.get()
        server_dt = datetime.fromtimestamp(server_ms / 1000.0, tz=timezone.utc)
        server_str = server_dt.strftime("%H:%M:%S.") + str(
            server_dt.microsecond // 1000
        ).zfill(3)

        return span(
            {
                "class": "server-time",
                "data-server-ms": str(int(server_ms)),
            },
            server_str,
        )


class TwoClocks(Component):
    """Component that displays server time, client time, and their skew.

    Server time is pushed via the real-time transport (WS/SSE) — no polling.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._server_time = signal(time.time() * 1000)
        self._running = False
        self._task = None
        self.server_time_comp = None

    def mount(self) -> None:
        self._running = True
        import asyncio

        self._task = asyncio.create_task(self._tick_loop())
        # Mount the child sub-component to isolate reactive updates
        self.server_time_comp = self._session.mount_component(
            "server-time-display",
            cid=f"{self.component_id}-server-time",
            server_time=self._server_time,
        )

    def unmount(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()

    @server
    def tick(self):
        self._server_time.set(time.time() * 1000)

    async def _tick_loop(self) -> None:
        import asyncio

        while self._running:
            try:
                # If a real transport (WS/SSE) is active, continuously push updates to the client
                if hasattr(self, "_session") and self._session.transport.is_connected():
                    self._server_time.set(time.time() * 1000)
                await asyncio.sleep(
                    0.016
                )  # High frequency ~60fps refresh rate on the backend
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def render(self):
        from hiccl.hiccup import raw

        # Render the child component
        child_html = self._session.renderer.render_component(self.server_time_comp)

        return div(
            {
                "class": "card bg-base-200 shadow-xl border border-base-300 mx-auto w-full max-w-2xl"
            },
            div(
                {"class": "card-body"},
                h2(
                    {"class": "card-title text-2xl font-bold mb-4 justify-center"},
                    "Two Clocks",
                ),
                div(
                    {
                        "class": "stats stats-vertical lg:stats-horizontal shadow bg-base-100 border border-base-200 w-full",
                        "hx-post": self.tick,
                        "hx-trigger": "every 1s",
                    },
                    div(
                        {"class": "stat"},
                        div({"class": "stat-title"}, "🖥  Server Time"),
                        div(
                            {
                                "class": "stat-value text-accent text-xl md:text-2xl font-mono"
                            },
                            raw(child_html),
                        ),
                        div({"class": "stat-desc"}, "SSE/WS Backend Push"),
                    ),
                    div(
                        {
                            "class": "stat",
                            "x-data": "{ clientTime: '…', skew: '…' }",
                            "x-init": (
                                "setInterval(() => {"
                                "  var d = new Date();"
                                "  clientTime = d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');"
                                "  var el = $el.closest('.stats').querySelector('.server-time');"
                                "  if (el) {"
                                "    var s = parseFloat(el.getAttribute('data-server-ms'));"
                                "    skew = Math.round(Date.now() - s) + ' ms';"
                                "  }"
                                "}, 16)"
                            ),
                        },
                        div({"class": "stat-title"}, "💻  Client Time"),
                        div(
                            {
                                "class": "stat-value text-primary text-xl md:text-2xl font-mono",
                                "x-text": "clientTime",
                            },
                            "…",
                        ),
                        div(
                            {"class": "stat-desc", "x-text": "'⏱  Skew: ' + skew"},
                            "Local Skew",
                        ),
                    ),
                ),
            ),
        )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

registry = ComponentRegistry()
registry.register("server-time-display", ServerTimeDisplay)

app = create_hiccl_app(
    HicclConfig(
        component_registry=registry,
        transport_modes={"http", "ws", "sse"},
        pages=menu(TwoClocks),
    )
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
