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
        session = Session(session_id, registry, renderer, store=session_store)
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

    Executes the @server method and returns the re-rendered component
    HTML directly. The real-time transport (SSE/WS) handles pushing
    updates to *other* sessions independently via EventBus broadcast.
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
        action_res = await session.execute_action(component_id, method_name, body)
        from starlette.responses import Response as StarletteResponse

        if isinstance(action_res, StarletteResponse):
            return action_res
    except Exception as e:
        return HTMLResponse(str(e), status_code=500)

    # Always return rendered HTML directly.
    # Using render_component_cached to also update the renderer cache,
    # so the SSE scheduler won't double-push the same content.
    html = session.renderer.render_component_cached(component)
    if html is None:
        html = ""  # No change (should not happen after an action)
    return HTMLResponse(html)
