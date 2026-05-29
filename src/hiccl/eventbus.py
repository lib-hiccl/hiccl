"""Hiccl EventBus — cross-session broadcast for real-time updates."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import Any

# 全局通配符正则表达式编译缓存，保障极高的路由分发性能
_pattern_cache: dict[str, re.Pattern] = {}


def match_topic(pattern: str, topic: str) -> bool:
    """根据 MQTT 风格的通配符匹配主题。

    以 '.' 作为层级分隔符。
    '*' 代表匹配单层：如 'chat.*' 匹配 'chat.room1'，但不匹配 'chat.room1.msg'。
    '#' 代表匹配零层或多层：如 'chat.#' 匹配 'chat'、'chat.room1'、'chat.room1.msg'。
    """
    if pattern == topic:
        return True
    if "*" not in pattern and "#" not in pattern:
        return pattern == topic

    if pattern not in _pattern_cache:
        # 转义正则特殊字符
        escaped = re.escape(pattern)
        # 1. '\.#' 替换为 '(?:\..*)?' (匹配包含前导点在内的多层，包含0层)
        # 2. '\#' 替换为 '.*' (匹配多层)
        # 3. '\*' 替换为 '[^.]+' (匹配非点字符单层)
        regex_str = (
            escaped.replace(r"\.\#", r"(?:\..*)?")
            .replace(r"\#", r".*")
            .replace(r"\*", r"[^.]+")
        )
        _pattern_cache[pattern] = re.compile("^" + regex_str + "$")

    return bool(_pattern_cache[pattern].match(topic))


class EventBus:
    """Global event bus for publishing component updates across sessions.

    Supports advanced wildcard subscriptions (MQTT-style `*` and `#`).

    Usage::

        from hiccl.eventbus import event_bus

        # Subscribe (typically in transport/SSE/WS handler)
        queue = asyncio.Queue()
        event_bus.subscribe("chat.*", queue)

        # Publish (typically after @server method execution)
        await event_bus.publish("chat.room1", {"action": "new_message"})

        # Unsubscribe on disconnect
        event_bus.unsubscribe("chat.*", queue)
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
        """Publish *data* to all subscribers matching *topic* (including wildcard subscribers).

        Uses ``put_nowait`` and silently drops events on full queues
        (removes those queues from the subscriber list).
        """
        dead_subscribers: dict[str, list[asyncio.Queue[Any]]] = defaultdict(list)

        # 统一包装为包含 'topic' 的规范字典信封，确保在 Session processing 中不被丢弃
        envelope = data
        if not isinstance(envelope, dict) or "topic" not in envelope:
            envelope = {
                "topic": topic,
                "data": data,
                "source": None,
                "source_session": None,
            }

        # Deduplicate target queues across all matching patterns to ensure
        # that a queue subscribed to multiple overlapping wildcard topics receives each message exactly once.
        queues_to_deliver: set[asyncio.Queue[Any]] = set()
        for pattern, queues in list(self._subscribers.items()):
            if match_topic(pattern, topic):
                for queue in queues:
                    queues_to_deliver.add(queue)

        for queue in queues_to_deliver:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                for pattern, queues in list(self._subscribers.items()):
                    if queue in queues:
                        dead_subscribers[pattern].append(queue)

        for pattern, dead_queues in dead_subscribers.items():
            for q in dead_queues:
                self._subscribers[pattern].discard(q)
            if not self._subscribers[pattern]:
                del self._subscribers[pattern]

    def publish_sync(self, topic: str, data: Any = None) -> None:
        """Synchronous publish — schedules ``publish`` on the event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(topic, data))
        except RuntimeError:
            pass


# Global singleton
event_bus = EventBus()
