"""Chat Room — Hiccl multi-user chat with real-time cross-session sync.

Demonstrates:
  - on_submit auto-binding (no manual htmx attributes)
  - EventBus cross-session broadcast (all users see new messages instantly)
  - Component.topics + on_broadcast for reactive updates
"""

from datetime import datetime

from hiccl import (
    Component,
    ComponentRegistry,
    HicclConfig,
    create_hiccl_app,
    menu,
    server,
    signal,
)
from hiccl.hiccup import button, div, form, h2, input_, li, span, ul

# ---------------------------------------------------------------------------
# Shared message store (all sessions see the same messages)
# ---------------------------------------------------------------------------
messages: list[dict] = []

registry = ComponentRegistry()


class ChatRoom(Component):
    """Chat room component with EventBus-powered real-time sync."""

    topics = ["chat-messages"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = signal(list(messages))

    @server
    def send_message(self, text: str = "", user: str = "Anonymous"):
        if not text.strip():
            return
        msg = {
            "user": user,
            "text": text,
            "time": datetime.now().isoformat(),
        }
        messages.append(msg)
        self.messages.set(list(messages))

    def on_broadcast(self, topic: str) -> None:
        """Called when EventBus publishes to our topic — refresh from shared store."""
        if topic == "chat-messages":
            self.messages.set(list(messages))

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


app = create_hiccl_app(HicclConfig(component_registry=registry, pages=menu(ChatRoom)))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
