"""Hiccl EventBus — cross-session broadcast for real-time updates."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    """Global event bus for publishing component updates across sessions.

    Usage::

        from hiccl.eventbus import event_bus

        # Subscribe (typically in transport/SSE/WS handler)
        queue = asyncio.Queue()
        event_bus.subscribe("chat-messages", queue)

        # Publish (typically after @server method execution)
        await event_bus.publish("chat-messages", {"action": "new_message"})

        # Unsubscribe on disconnect
        event_bus.unsubscribe("chat-messages", queue)
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Any]]] = defaultdict(set)

    def subscribe(self, topic: str, queue: asyncio.Queue[Any]) -> None:
        """Register *queue* to receive events for *topic*."""
        self._subscribers[topic].add(queue)

    def unsubscribe(self, topic: str, queue: asyncio.Queue[Any]) -> None:
        """Remove *queue* from *topic*.  Cleans up empty topic sets."""
        self._subscribers[topic].discard(queue)
        if not self._subscribers[topic]:
            del self._subscribers[topic]

    def unsubscribe_all(self, queue: asyncio.Queue[Any]) -> None:
        """Remove *queue* from all topics."""
        for topic in list(self._subscribers.keys()):
            self._subscribers[topic].discard(queue)
            if not self._subscribers[topic]:
                del self._subscribers[topic]

    async def publish(self, topic: str, data: Any = None) -> None:
        """Publish *data* to all subscribers of *topic*.

        Uses ``put_nowait`` and silently drops events on full queues
        (removes those queues from the subscriber list).
        """
        if topic not in self._subscribers:
            return
        dead: list[asyncio.Queue[Any]] = []
        for queue in self._subscribers[topic]:
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self._subscribers[topic].discard(q)

    def publish_sync(self, topic: str, data: Any = None) -> None:
        """Synchronous publish — schedules ``publish`` on the event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(topic, data))
        except RuntimeError:
            pass


# Global singleton
event_bus = EventBus()
