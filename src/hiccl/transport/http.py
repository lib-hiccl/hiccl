"""Hiccl HTTP transport — htmx AJAX action handler."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/hiccl")


async def get_session(request: Request, response: Response):
    """FastAPI dependency: get or create session from cookie / header."""
    from hiccl.session import Session

    hiccl_state = request.app.state.hiccl
    session_store = hiccl_state["session_store"]

    session_id = request.cookies.get("hiccl_sid") or request.query_params.get(
        "session_id"
    )
    is_new = False
    if not session_id:
        session_id = uuid.uuid4().hex
        is_new = True

    session = await session_store.get(session_id)
    if session is None:
        registry = hiccl_state["registry"]
        renderer = hiccl_state["renderer"]
        session = Session(session_id, registry, renderer)
        await session_store.save(session)
        is_new = True

    session.touch()

    # Store the session_id in request.state so that layout builders can extract it on first page load
    request.state.hiccl_session_id = session_id

    if is_new:
        response.set_cookie(
            "hiccl_sid", session_id, httponly=True, samesite="lax", path="/"
        )

    return session


@router.post("/action/{component_id}/{method_name}")
async def handle_action(
    component_id: str,
    method_name: str,
    request: Request,
    session=Depends(get_session),
):
    """Handle an htmx AJAX action POST.

    If the session has a connected push transport (WS/SSE), the rendered
    HTML is pushed through that channel and we return an empty 200.
    Otherwise (pure HTTP mode), the rendered HTML is returned directly.
    """
    component = session.get_component(component_id)
    if component is None:
        return HTMLResponse("Component not found", status_code=404)

    from hiccl.component import get_server_methods

    methods = get_server_methods(component)
    if method_name not in methods:
        return HTMLResponse(f"Method '{method_name}' not found", status_code=404)

    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
        else:
            body = dict(request.query_params)
            form_data = await request.form()
            body.update({k: v for k, v in form_data.items()})

        # Execute via session (handles EventBus auto-publish)
        await session.execute_action(component_id, method_name, body)
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)

    # If a real-time transport is connected, the update is pushed there
    if session.transport.is_connected():
        return HTMLResponse("", status_code=200)

    # Pure HTTP: return rendered HTML directly
    html = session.renderer.render_component(component)
    return HTMLResponse(html)
