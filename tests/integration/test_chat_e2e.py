"""Integration test — Chat Room multi-session sync and EventBus broadcast."""

import pytest
from fastapi.testclient import TestClient

from examples.chat.app import ChatRoom, messages
from hiccl import (
    ComponentRegistry,
    HicclConfig,
    create_hiccl_app,
)
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions


@pytest.fixture(autouse=True)
def clean_messages():
    """Clear shared messages store before each test."""
    messages.clear()


@pytest.fixture
def chat_app():
    registry = ComponentRegistry()
    registry.register("chat-room", ChatRoom)

    config = HicclConfig(
        component_registry=registry,
        transport_modes={"http", "ws"},
    )
    app = create_hiccl_app(config)

    # Set up two sessions representing two different users
    session1 = Session("session-user-1", registry, HiccupRenderer())
    comp1 = session1.mount_component("chat-room", cid="chat-room-1")
    _sessions["session-user-1"] = session1

    session2 = Session("session-user-2", registry, HiccupRenderer())
    comp2 = session2.mount_component("chat-room", cid="chat-room-2")
    _sessions["session-user-2"] = session2

    return app, comp1, comp2, session1, session2


class TestChatE2E:
    def test_initial_render(self, chat_app):
        app, comp1, comp2, _, _ = chat_app
        html1 = HiccupRenderer().render_component(comp1)
        html2 = HiccupRenderer().render_component(comp2)

        assert "Chat Room" in html1
        assert "Chat Room" in html2
        assert "Anonymous" in html1

    def test_send_message_sync(self, chat_app):
        app, comp1, comp2, s1, s2 = chat_app

        # User 1 sends a message via HTTP post action
        with TestClient(app, cookies={"hiccl_sid": "session-user-1"}) as client:
            resp = client.post(
                "/hiccl/action/chat-room-1/send_message",
                data={"text": "Hello world", "user": "Alice"},
            )
            assert resp.status_code == 200
            assert "Alice" in resp.text
            assert "Hello world" in resp.text

            # Check that User 1's local signal is updated
            msgs1 = comp1.messages.get()
            assert len(msgs1) == 1
            assert msgs1[0]["user"] == "Alice"
            assert msgs1[0]["text"] == "Hello world"

            # Check that User 2's session processes EventBus events
            # (which simulates the background event loop in SSE/WS transport)
            import asyncio

            asyncio.run(s2.process_eventbus_events())

            # Now, comp2's signal should be updated with the broadcasted message!
            msgs2 = comp2.messages.get()
            assert len(msgs2) == 1
            assert msgs2[0]["user"] == "Alice"
            assert msgs2[0]["text"] == "Hello world"

            # Check that the next render of comp2 contains Alice's message
            html2 = HiccupRenderer().render_component(comp2)
            assert "Alice" in html2
            assert "Hello world" in html2

    def test_send_message_sync_same_cid(self, chat_app):
        # Set up a new pair of sessions with identical component IDs ("chat-room-main")
        registry = ComponentRegistry()
        registry.register("chat-room", ChatRoom)

        config = HicclConfig(
            component_registry=registry,
            transport_modes={"http", "ws"},
        )
        app = create_hiccl_app(config)

        s1 = Session("session-user-1-same", registry, HiccupRenderer())
        comp1 = s1.mount_component("chat-room", cid="chat-room-main")
        _sessions["session-user-1-same"] = s1

        s2 = Session("session-user-2-same", registry, HiccupRenderer())
        comp2 = s2.mount_component("chat-room", cid="chat-room-main")
        _sessions["session-user-2-same"] = s2

        with TestClient(app, cookies={"hiccl_sid": "session-user-1-same"}) as client:
            # User 1 sends a message via HTTP post action
            resp = client.post(
                "/hiccl/action/chat-room-main/send_message",
                data={"text": "Hello all", "user": "Bob"},
            )
            assert resp.status_code == 200

            # Simulate the background event loop in SSE/WS transport for both sessions
            import asyncio

            asyncio.run(s1.process_eventbus_events())
            asyncio.run(s2.process_eventbus_events())

            # User 1 (originator) should have the message in its signal
            msgs1 = comp1.messages.get()
            assert len(msgs1) == 1
            assert msgs1[0]["user"] == "Bob"

            # User 2 should ALSO have the message in its signal now!
            msgs2 = comp2.messages.get()
            assert len(msgs2) == 1
            assert msgs2[0]["user"] == "Bob"
