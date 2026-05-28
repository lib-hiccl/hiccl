"""Combined App — showcasing component-based routing and auto-menu generation in Hiccl.

Run this application to see Counter, TwoClocks and ChatRoom working together with a unified premium navigation bar!
"""

import time
import asyncio
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
from hiccl.hiccup import button, div, form, h2, input_, li, span, ul, raw


# 1. Counter Component
class Counter(Component):
    """极简的响应式计数器。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = signal(0)

    @server
    def increment(self, step: int = 1):
        if isinstance(step, str):
            step = int(step)
        self.count.set(self.count.get() + step)

    @server
    def decrement(self, step: int = 1):
        if isinstance(step, str):
            step = int(step)
        self.count.set(self.count.get() - step)

    @server
    def reset(self):
        self.count.set(0)

    def render(self):
        count = self.count.get()
        return div(
            {"class": "card w-96 bg-base-200 shadow-xl border border-base-300 mx-auto"},
            div(
                {"class": "card-body items-center text-center"},
                h2(
                    {"class": "card-title text-3xl font-extrabold mb-4"},
                    f"Count: {count}",
                ),
                div(
                    {"class": "card-actions justify-center gap-2"},
                    button(
                        {
                            "class": "btn btn-outline btn-error",
                            "on_click": self.decrement(5),
                        },
                        "-5",
                    ),
                    button(
                        {"class": "btn btn-error", "on_click": self.decrement(1)}, "-1"
                    ),
                    button(
                        {"class": "btn btn-neutral", "on_click": self.reset}, "Reset"
                    ),
                    button(
                        {"class": "btn btn-success", "on_click": self.increment(1)},
                        "+1",
                    ),
                    button(
                        {
                            "class": "btn btn-outline btn-success",
                            "on_click": self.increment(5),
                        },
                        "+5",
                    ),
                ),
            ),
        )


# 2. TwoClocks Components
class ServerTimeDisplay(Component):
    """展示服务器端时间高频更新的子组件。"""

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
                "id": f"{self.component_id}-server-time",
                "data-server-ms": str(int(server_ms)),
            },
            server_str,
        )


class TwoClocks(Component):
    """显示服务器时间、客户端时间以及它们之间 skew (偏差) 的双时钟组件。"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._server_time = signal(time.time() * 1000)
        self._running = False
        self._task = None
        self.server_time_comp = None

    def mount(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._tick_loop())
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
        while self._running:
            try:
                if hasattr(self, "_session") and self._session.transport.is_connected():
                    self._server_time.set(time.time() * 1000)
                await asyncio.sleep(0.016)  # ~60fps backend ticks
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def render(self):
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


# 3. ChatRoom Component
shared_messages: list[dict] = []


class ChatRoom(Component):
    """聊天室组件，支持跨会话的多人实时同步聊天。"""

    topics = ["chat-messages"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = signal(list(shared_messages))

    @server
    def send_message(self, text: str = "", user: str = "Anonymous"):
        if not text.strip():
            return
        msg = {
            "user": user,
            "text": text,
            "time": datetime.now().isoformat(),
        }
        shared_messages.append(msg)
        self.messages.set(list(shared_messages))

    def on_broadcast(self, topic: str) -> None:
        if topic == "chat-messages":
            self.messages.set(list(shared_messages))

    def render(self):
        msgs = self.messages.get()
        return div(
            {
                "class": "card bg-base-200 shadow-xl border border-base-300 mx-auto w-full max-w-2xl"
            },
            div(
                {"class": "card-body"},
                h2(
                    {"class": "card-title text-2xl font-bold mb-4 justify-center"},
                    "Chat Room",
                ),
                div(
                    {
                        "class": "bg-base-100 border border-base-300 rounded-xl p-4 h-96 overflow-y-auto flex flex-col gap-4"
                    },
                    *[
                        div(
                            {
                                "class": f"chat {'chat-end' if m['user'] == 'Me' or m['user'] == 'Anonymous' else 'chat-start'}"
                            },
                            div(
                                {"class": "chat-header opacity-50 text-xs mb-1"},
                                m["user"],
                            ),
                            div(
                                {
                                    "class": f"chat-bubble {'chat-bubble-primary' if m['user'] == 'Me' or m['user'] == 'Anonymous' else 'chat-bubble-secondary'}"
                                },
                                m["text"],
                            ),
                            div(
                                {"class": "chat-footer opacity-50 text-[10px] mt-1"},
                                m["time"].split("T")[1][:8] if "T" in m["time"] else "",
                            ),
                        )
                        for m in msgs
                    ],
                ),
                form(
                    {"class": "join mt-4 w-full", "on_submit": self.send_message},
                    input_(
                        {
                            "type": "text",
                            "name": "user",
                            "class": "input input-bordered join-item w-28",
                            "placeholder": "Name",
                            "value": "Anonymous",
                        }
                    ),
                    input_(
                        {
                            "type": "text",
                            "name": "text",
                            "class": "input input-bordered join-item flex-1",
                            "placeholder": "Message...",
                            "required": True,
                        }
                    ),
                    button(
                        {"class": "btn btn-primary join-item", "type": "submit"}, "Send"
                    ),
                ),
            ),
        )


# 4. Application Setup
registry = ComponentRegistry()
registry.register("server-time-display", ServerTimeDisplay)

app = create_hiccl_app(
    HicclConfig(
        component_registry=registry,
        transport_modes={"http", "ws", "sse"},
        pages=menu(Counter, TwoClocks, ChatRoom),
        brand_name="Hiccl Combined Demo",
        theme="night",
    )
)


if __name__ == "__main__":
    import uvicorn

    print("启动 Hiccl 离线/DaisyUI/Alpine 联合演示应用...")
    print("访问地址: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
