"""Hiccl WebSocket transport — real-time bidirectional handler."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


# ---------------------------------------------------------------------------
# WS Transport adapter
# ---------------------------------------------------------------------------


class WSTransport:
    """Transport that pushes patches through a WebSocket connection."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket
        self._connected = True

    async def push(self, patches: list[dict]) -> None:
        if self._connected:
            try:
                await self._ws.send_json({"type": "batch", "patches": patches})
            except Exception:
                self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def disconnect(self) -> None:
        self._connected = False


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/hiccl/ws/{session_id}")
async def hiccl_websocket(websocket: WebSocket, session_id: str):
    """WebSocket handler for real-time component updates.

    Flow:
        1. Accept connection, set up WSTransport + RenderScheduler.
        2. Signal changes → RenderScheduler → render dirty → push via WS.
        3. EventBus messages → on_broadcast → signal changes → same flow.
        4. Incoming JSON actions → execute_action → auto-publish to EventBus.
        5. On disconnect: session is NOT immediately disposed (supports reconnect).
    """
    from hiccl.scheduler import RenderScheduler
    from hiccl.transport.protocol import NullTransport

    await websocket.accept()

    hiccl_state = getattr(websocket.app.state, "hiccl", {})
    session_store = (
        hiccl_state.get("session_store") if isinstance(hiccl_state, dict) else None
    )
    session = await session_store.get(session_id) if session_store else None

    if session is None:
        await websocket.close(code=4404, reason="Session not found")
        return

    transport = WSTransport(websocket)
    session.transport = transport

    hiccl_state = getattr(websocket.app.state, "hiccl", {})
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
            component = session.get_component(cid)
            if component is None:
                continue
            html = session.renderer.render_component_cached(component)
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
        if patches and transport.is_connected():
            await transport.push(patches)

    scheduler.start(asyncio.get_event_loop(), render_fn, push_fn)

    try:
        while transport.is_connected():
            # Process EventBus events → on_broadcast → signal changes
            await session.process_eventbus_events()

            # Wait for incoming messages with a timeout to allow EventBus processing
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except Exception:
                break

            msg_type = message.get("type")

            if msg_type == "action":
                cid = message.get("component_id", "")
                method = message.get("method", "")
                args = message.get("args", {})
                try:
                    await session.execute_action(cid, method, args)
                except Exception as e:
                    if transport.is_connected():
                        await websocket.send_json(
                            {
                                "type": "error",
                                "component_id": cid,
                                "message": str(e),
                                "status": 500,
                            }
                        )

            elif msg_type == "reconnect":
                # Client is reconnecting — re-send all component HTML
                patches = []
                for cid, comp in session._components.items():
                    html = session.renderer.render_component(comp)
                    patches.append(
                        {
                            "type": "patch",
                            "component_id": cid,
                            "html": html,
                            "swap": "outerHTML",
                        }
                    )
                if patches and transport.is_connected():
                    await transport.push(patches)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        transport.disconnect()
        session.transport = NullTransport()
        session.on_signal_change = None
        await scheduler.stop()
        # Note: session is NOT disposed here to support reconnect
        # Session cleanup happens via app shutdown or timeout
