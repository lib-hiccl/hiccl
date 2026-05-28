"""Hiccl RenderScheduler — bridges sync signal propagation to async rendering."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Awaitable

logger = logging.getLogger("hiccl.scheduler")


class RenderScheduler:
    """Bridge synchronous signal propagation to async render queue.

    Architecture:
        Sync side (Signal → Effect)
            │
            ▼
        mark_dirty(component_id)  ← Effect callback (sync)
            │
            ▼
        asyncio.Event.set()
            │
            ▼
        async tick() loop          ← FastAPI event loop
            │
            ▼
        render_fn(dirty_ids)       ← batch render Hiccup → HTML
            │
            ▼
        push_fn(patches)           ← WebSocket/SSE push
    """

    def __init__(self, coalesce_ms: float = 0.0) -> None:
        self._dirty: set[str] = set()
        self._event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self.coalesce_ms = coalesce_ms

    def mark_dirty(self, component_id: str) -> None:
        """Called from Effect callback (sync side of signal propagation)."""
        self._dirty.add(component_id)
        self._event.set()

    async def tick(
        self,
        render_fn: Callable[[set[str]], Awaitable[list[dict]]],
        push_fn: Callable[[list[dict]], Awaitable[None]],
    ) -> None:
        """Run in FastAPI event loop — processes dirty components and pushes patches."""
        while True:
            await self._event.wait()
            self._event.clear()
            if self.coalesce_ms > 0:
                await asyncio.sleep(self.coalesce_ms / 1000.0)
            dirty = self._dirty.copy()
            self._dirty.clear()
            if dirty:
                try:
                    patches = await render_fn(dirty)
                    if patches:
                        await push_fn(patches)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.exception("Error during scheduler tick: %s", e)

    def start(
        self,
        loop: asyncio.AbstractEventLoop,
        render_fn: Callable[[set[str]], Awaitable[list[dict]]],
        push_fn: Callable[[list[dict]], Awaitable[None]],
    ) -> None:
        """Start the scheduler tick loop as a task on the given event loop."""
        self._task = loop.create_task(self.tick(render_fn, push_fn))

    async def stop(self) -> None:
        """Stop the scheduler and cancel the tick task."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
