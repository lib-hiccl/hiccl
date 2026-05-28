"""Hiccl Session — per-connection state management with transport & EventBus."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from hiccl.component import Component, get_server_methods
from hiccl.eventbus import event_bus
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.signal import Effect
from hiccl.transport.protocol import NullTransport, Transport

# Global session store
_sessions: dict[str, Session] = {}


class Session:
    """Per-connection state: holds mounted components, effects, and transport.

    Attributes:
        session_id:      Unique session identifier.
        transport:       Push channel (WS, SSE, or NullTransport).
        on_signal_change: Callback invoked when a watched signal changes.
    """

    def __init__(
        self,
        session_id: str,
        registry: ComponentRegistry,
        renderer: HiccupRenderer,
    ) -> None:
        self.session_id = session_id
        self._components: dict[str, Component] = {}
        self._registry = registry
        self.renderer = renderer
        self.on_signal_change: Callable[[str], None] | None = None
        self.transport: Transport = NullTransport()
        self.last_accessed: float = time.time()

        # EventBus integration
        self._event_queue: asyncio.Queue[Any] | None = None
        self._subscribed_topics: set[str] = set()

    def touch(self) -> None:
        """Refresh the last accessed timestamp."""
        self.last_accessed = time.time()

    # -- Component lifecycle -----------------------------------------------

    def mount_component(
        self, name: str, cid: str | None = None, **props: Any
    ) -> Component:
        """Create and mount a component instance."""
        self.touch()
        component = self._registry.create(name, **props)
        if cid:
            component.component_id = cid
        self._components[component.component_id] = component
        component._session = self
        component.mount()

        # Subscribe to EventBus topics declared by the component
        topics = getattr(component, "topics", [])
        if topics:
            if self._event_queue is None:
                self._event_queue = asyncio.Queue()
            for topic in topics:
                if topic not in self._subscribed_topics:
                    event_bus.subscribe(topic, self._event_queue)
                    self._subscribed_topics.add(topic)

        # Create effects that watch all component signals
        for sig_name in component._signals:
            sig = component._signals[sig_name]

            def make_effect(signal_obj, comp_id):
                def watch():
                    signal_obj.get()
                    if self.on_signal_change:
                        self.on_signal_change(comp_id)

                return watch

            effect = Effect(make_effect(sig, component.component_id))
            component._effects.append(effect)

        return component

    def get_component(self, component_id: str) -> Component | None:
        """Look up a mounted component by ID."""
        self.touch()
        return self._components.get(component_id)

    # -- Action execution --------------------------------------------------

    async def execute_action(
        self, component_id: str, method_name: str, args: dict[str, Any]
    ) -> Any:
        """Execute a ``@server`` method and auto-publish to EventBus.

        Returns the method's return value (if any).
        """
        self.touch()
        component = self._components.get(component_id)
        if component is None:
            return None

        methods = get_server_methods(component)
        if method_name not in methods:
            return None

        result = methods[method_name](**args)
        if asyncio.iscoroutine(result):
            await result

        # Auto-publish to EventBus for the component's topics
        topics = getattr(component, "topics", [])
        for topic in topics:
            await event_bus.publish(
                topic,
                {
                    "topic": topic,
                    "source": component_id,
                    "source_session": self.session_id,
                },
            )

        return result

    # -- EventBus processing -----------------------------------------------

    async def process_eventbus_events(self) -> None:
        """Drain EventBus queue and trigger ``on_broadcast`` on components.

        Should be called periodically by the transport handler (WS/SSE).
        """
        self.touch()
        if self._event_queue is None:
            return
        while not self._event_queue.empty():
            try:
                msg = self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if not isinstance(msg, dict):
                continue
            topic = msg.get("topic")
            source_cid = msg.get("source")
            source_session = msg.get("source_session")
            for cid, comp in self._components.items():
                # Skip the originator — it already updated its own signal
                if self.session_id == source_session and cid == source_cid:
                    continue
                comp_topics = getattr(comp, "topics", [])
                if topic in comp_topics:
                    comp.on_broadcast(topic)

    # -- Cleanup -----------------------------------------------------------

    def dispose(self) -> None:
        """Dispose all mounted components, effects, and EventBus subscriptions."""
        # Unsubscribe from EventBus
        if self._event_queue is not None:
            event_bus.unsubscribe_all(self._event_queue)
            self._event_queue = None
        self._subscribed_topics.clear()

        # Dispose components
        for component in self._components.values():
            for effect in component._effects:
                effect.dispose()
            component._effects.clear()
            component.unmount()
        self._components.clear()
