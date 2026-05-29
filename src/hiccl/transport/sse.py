"""Hiccl SSE transport — Server-Sent Events handler with real-time push."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# SSE Transport adapter
# ---------------------------------------------------------------------------


class SSETransport:
    """Transport that pushes patches via an asyncio.Queue (consumed by SSE stream)."""

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue
        self._connected = True

    async def push(self, patches: list[dict]) -> None:
        data = json.dumps({"type": "batch", "patches": patches})
        await self._queue.put(f"event: hiccl\ndata: {data}\n\n")

    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------


async def get_session_sse(session_id: str, request: Request):
    """Dependency: look up session from URL path."""
    hiccl_state = getattr(request.app.state, "hiccl", {})
    session_store = (
        hiccl_state.get("session_store") if isinstance(hiccl_state, dict) else None
    )

    session = await session_store.get(session_id) if session_store else None
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/hiccl/sse/{session_id}")
async def hiccl_sse(
    session_id: str, request: Request, session=Depends(get_session_sse)
):
    """SSE endpoint — streams component updates to the client.

    Flow:
        1. Create SSETransport + RenderScheduler for this session.
        2. Signal changes → RenderScheduler → render dirty → push via SSE.
        3. EventBus messages → on_broadcast → signal changes → same flow.
        4. Heartbeat every 15 s for keepalive.
    """
    from hiccl.scheduler import RenderScheduler

    sse_queue: asyncio.Queue[str] = asyncio.Queue()
    transport = SSETransport(sse_queue)
    session.transport = transport

    hiccl_state = getattr(request.app.state, "hiccl", {})
    config = hiccl_state.get("config") if isinstance(hiccl_state, dict) else None
    coalesce_ms = getattr(config, "scheduler_coalesce_ms", 0.0) if config else 0.0
    scheduler = RenderScheduler(coalesce_ms=coalesce_ms)

    # Force a silent initial render of all mounted components that don't have active effects
    # to register all reactive effects, subscription watches, and setup their dependency tracking
    # while session.on_signal_change is STILL None. This prevents any render-phase signal modifications
    # from triggering recursive dirty marking or infinite scheduler loops.
    for comp in list(session._components.values()):
        if not comp._effects:
            session.renderer.render_component(comp)

    session.on_signal_change = scheduler.mark_dirty

    async def render_fn(dirty_ids: set[str]) -> list[dict]:
        patches = []
        for cid in dirty_ids:
            comp = session.get_component(cid)
            if comp is None:
                continue
            html = session.renderer.render_component_cached(comp)
            if html is None:
                continue
            patches.append(
                {
                    "type": "patch",
                    "component_id": cid,
                    "html": html,
                    "swap": "outerHTML",
                }
            )
        return patches

    async def push_fn(patches: list[dict]) -> None:
        if patches:
            data = json.dumps({"type": "batch", "patches": patches})
            await sse_queue.put(f"event: hiccl\ndata: {data}\n\n")

    async def event_stream():
        import time

        loop = asyncio.get_event_loop()
        scheduler.start(loop, render_fn, push_fn)
        heartbeat_interval = 15  # seconds
        last_heartbeat = 0.0
        try:
            while transport.is_connected():
                # Drain SSE queue (rendered patches)
                while not sse_queue.empty():
                    try:
                        event = sse_queue.get_nowait()
                        yield event
                    except asyncio.QueueEmpty:
                        break

                # Process EventBus → on_broadcast → signal changes → scheduler
                await session.process_eventbus_events()

                # Throttled heartbeat
                now = time.monotonic()
                if now - last_heartbeat >= heartbeat_interval:
                    yield "event: heartbeat\ndata: \n\n"
                    last_heartbeat = now

                await asyncio.sleep(0.05)  # 20 Hz check rate
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            transport.disconnect()
            from hiccl.transport.protocol import NullTransport

            session.transport = NullTransport()
            await scheduler.stop()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
