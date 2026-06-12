"""Hiccl App — FastAPI application factory and configuration."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session_store import MemorySessionStore, SessionStore


logger = logging.getLogger("hiccl.app")

if TYPE_CHECKING:
    from hiccl.component import Component


class CascadeStaticFiles(StaticFiles):
    """StaticFiles subclass that searches multiple directories in order."""

    def __init__(self, directories: list[str], **kwargs):
        import os

        existing_dirs = [d for d in directories if os.path.isdir(d)]
        if not existing_dirs:
            raise RuntimeError(f"None of the directories exist: {directories}")
        super().__init__(directory=existing_dirs[0], **kwargs)
        self.all_directories = existing_dirs


def _generate_font_tags(config: HicclConfig) -> str:
    if getattr(config, "offline_mode", False):
        return """  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
  </style>"""
    else:
        return """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    body {
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }
  </style>"""


def hiccl_raw_layout(
    request: Request, comp_html: str, menu_html: str, config: HicclConfig
) -> str:
    session_id = getattr(
        request.state, "hiccl_session_id", None
    ) or request.cookies.get(config.session_cookie_name, "")
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="{config.theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{config.title}</title>
  <meta name="hiccl-session" content="{session_id}">
  <link href="/static/daisyui.css" rel="stylesheet" type="text/css" />
  <script src="/static/tailwind.js"></script>
  <script defer src="/static/alpine.js"></script>
  <script src="/static/htmx.js"></script>
  <script src="/static/hiccl.js"></script>
  {config.head_extra}
</head>
<body>
  {comp_html}
</body>
</html>"""


def hiccl_default_layout(
    request: Request, comp_html: str, menu_html: str, config: HicclConfig
) -> str:
    session_id = getattr(
        request.state, "hiccl_session_id", None
    ) or request.cookies.get(config.session_cookie_name, "")

    navbar_html = ""
    if config.show_navbar and menu_html:
        navbar_html = f"""
  <div class="navbar bg-base-100 shadow-lg border-b border-base-200 px-6 py-4 w-full max-w-7xl rounded-b-xl">
    <div class="flex-1">
      <a class="text-2xl font-black bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent tracking-tight flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-accent animate-pulse shadow-[0_0_10px_var(--fallback-a,rgba(16,185,129,0.5))]"></span>
        {config.brand_name}
      </a>
    </div>
    <div class="flex-none">
      {menu_html}
    </div>
  </div>"""

    fonts_html = _generate_font_tags(config)

    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="{config.theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{config.title}</title>
  <meta name="hiccl-session" content="{session_id}">
  <link href="/static/daisyui.css" rel="stylesheet" type="text/css" />
  <script src="/static/tailwind.js"></script>
  <script defer src="/static/alpine.js"></script>
  <script src="/static/htmx.js"></script>
  <script src="/static/hiccl.js"></script>
  {fonts_html}
  {config.head_extra}
</head>
<body class="min-h-screen bg-base-300 flex flex-col items-center gap-6">
  {navbar_html}
  <main class="w-full max-w-7xl px-4 py-6 flex justify-center items-start">
    {comp_html}
  </main>
</body>
</html>"""


def hiccl_card_layout(
    request: Request, comp_html: str, menu_html: str, config: HicclConfig
) -> str:
    session_id = getattr(
        request.state, "hiccl_session_id", None
    ) or request.cookies.get(config.session_cookie_name, "")

    navbar_html = ""
    if config.show_navbar and menu_html:
        navbar_html = f"""
  <div class="navbar bg-base-100 shadow-lg border-b border-base-200 px-6 py-4 w-full max-w-7xl rounded-b-xl">
    <div class="flex-1">
      <a class="text-2xl font-black bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent tracking-tight flex items-center gap-2">
        <span class="w-3 h-3 rounded-full bg-accent animate-pulse shadow-[0_0_10px_var(--fallback-a,rgba(16,185,129,0.5))]"></span>
        {config.brand_name}
      </a>
    </div>
    <div class="flex-none">
      {menu_html}
    </div>
  </div>"""

    title_html = ""
    if config.description or config.title:
        desc_html = (
            f'<p class="text-base-content/60 max-w-md mx-auto">{config.description}</p>'
            if config.description
            else ""
        )
        title_html = f"""
    <div class="text-center mb-4">
      <h1 class="text-4xl font-extrabold tracking-tight mb-2 text-white">{config.title}</h1>
      {desc_html}
    </div>"""

    fonts_html = _generate_font_tags(config)

    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="{config.theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{config.title}</title>
  <meta name="hiccl-session" content="{session_id}">
  <link href="/static/daisyui.css" rel="stylesheet" type="text/css" />
  <script src="/static/tailwind.js"></script>
  <script defer src="/static/alpine.js"></script>
  <script src="/static/htmx.js"></script>
  <script src="/static/hiccl.js"></script>
  {fonts_html}
  {config.head_extra}
</head>
<body class="min-h-screen bg-base-300 flex flex-col items-center gap-6">
  {navbar_html}
  <main class="w-full max-w-4xl px-4 py-6 flex flex-col gap-6">
    {title_html}
    <div class="card bg-base-200 border border-base-300 shadow-xl p-6 flex justify-center items-center">
      {comp_html}
    </div>
  </main>
</body>
</html>"""


@dataclass
class HicclConfig:
    """Configuration for a Hiccl application."""

    component_registry: ComponentRegistry
    renderer: HiccupRenderer | None = None
    transport_modes: set[str] = field(default_factory=lambda: {"http", "ws"})
    session_cookie_name: str = "hiccl_sid"
    static_url: str | None = "/static"
    static_dir: str | None = "static"
    cors_origins: list[str] | None = None
    title: str = "Hiccl"
    version: str = "0.1.1"
    session_max_age: float = 1800.0  # 30 minutes
    session_cleanup_interval: float = 60.0  # 1 minute
    pages: dict[str, type[Component]] | None = None
    offline_mode: bool = True
    scheduler_coalesce_ms: float = 0.0
    session_store: SessionStore | None = None

    # Layout and customization parameters
    theme: str = "dark"
    brand_name: str = "Hiccl"
    show_navbar: bool = True
    description: str | None = None
    head_extra: str = ""
    layout: Callable[[Request, str, str, HicclConfig], str] = hiccl_default_layout

    # HMR & hREPL configurations (auto-detected from environment variables or explicitly passed)
    live_reload: bool = field(
        default_factory=lambda: os.environ.get("HICCL_LIVE_RELOAD") == "1"
    )
    hrepl_enabled: bool = field(
        default_factory=lambda: (
            os.environ.get("HREPL_ENABLED", "").lower() in ("true", "1")
        )
    )
    hrepl_port: int = field(
        default_factory=lambda: int(os.environ.get("HREPL_PORT", "8998"))
    )
    hrepl_host: str = field(
        default_factory=lambda: os.environ.get("HREPL_HOST", "127.0.0.1")
    )


async def _session_eviction_loop(
    session_store: SessionStore, interval: float, max_age: float
) -> None:
    """Periodically sweep and dispose of expired sessions."""
    while True:
        try:
            await asyncio.sleep(interval)
            await session_store.sweep_expired(max_age)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Error in session eviction loop: %s", e)


def create_hiccl_app(config: HicclConfig) -> FastAPI:
    """Create and return a configured FastAPI application."""

    if config.session_store is None:
        config.session_store = MemorySessionStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start session eviction background task
        eviction_task = asyncio.create_task(
            _session_eviction_loop(
                config.session_store,
                config.session_cleanup_interval,
                config.session_max_age,
            )
        )

        watcher_task = None
        if config.live_reload:
            from hiccl.live_reload.watcher import start_watcher

            watcher_task = asyncio.create_task(start_watcher(app))
            logger.info("HMR: File watcher task spawned")

        hrepl_server = None
        if config.hrepl_enabled:
            from hiccl.repl.server import HReplServer

            hrepl_server = HReplServer(
                host=config.hrepl_host, port=config.hrepl_port, app=app
            )
            await hrepl_server.start()

        try:
            yield
        finally:
            eviction_task.cancel()
            try:
                await eviction_task
            except asyncio.CancelledError:
                pass

            if watcher_task:
                watcher_task.cancel()
                try:
                    await watcher_task
                except asyncio.CancelledError:
                    pass

            if hrepl_server:
                await hrepl_server.stop()

            sessions = await config.session_store.list_sessions()
            for session in sessions:
                session.dispose()

    app = FastAPI(title=config.title, version=config.version, lifespan=lifespan)

    app.state.hiccl = {
        "registry": config.component_registry,
        "renderer": config.renderer or HiccupRenderer(),
        "session_store": config.session_store,
        "config": config,
    }

    if "http" in config.transport_modes:
        from hiccl.transport.http import router as http_router

        app.include_router(http_router)

    if "ws" in config.transport_modes:
        from hiccl.transport.websocket import router as ws_router

        app.include_router(ws_router)

    if "sse" in config.transport_modes:
        from hiccl.transport.sse import router as sse_router

        app.include_router(sse_router)

    if config.static_url and config.static_dir:
        import os

        package_root = os.path.abspath(os.path.dirname(__file__))
        pkg_static = os.path.join(package_root, "static")

        static_dirs = []
        user_static = config.static_dir

        if os.path.isdir(user_static):
            static_dirs.append(user_static)

        if os.path.isdir(pkg_static):
            static_dirs.append(pkg_static)

        if static_dirs:
            if len(static_dirs) == 1:
                app.mount(
                    config.static_url,
                    StaticFiles(directory=static_dirs[0]),
                    name="static",
                )
            else:
                app.mount(
                    config.static_url,
                    CascadeStaticFiles(directories=static_dirs),
                    name="static",
                )

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register component-based page routes
    _register_page_routes(app, config)

    return app


def _register_page_routes(app: FastAPI, config: HicclConfig) -> None:
    import re

    from fastapi.responses import HTMLResponse

    from hiccl.transport.http import get_session

    if not config.pages:
        return

    # First, make sure all components are registered in the registry
    for path, comp_cls in config.pages.items():
        comp_name = getattr(comp_cls, "_hiccl_component_name", None)
        if not comp_name:
            comp_name = (
                re.sub(r"(?<!^)(?=[A-Z])", "-", comp_cls.__name__).strip("-").lower()
            )
            comp_cls._hiccl_component_name = comp_name

        try:
            config.component_registry.resolve(comp_name)
        except ValueError:
            config.component_registry.register(comp_name, comp_cls)

    # Register each route GET handler
    for path, comp_cls in config.pages.items():
        comp_name = getattr(
            comp_cls, "_hiccl_component_name", comp_cls.__name__.lower()
        )

        def make_handler(p_path: str, p_cls: type[Component], p_name: str):
            async def handler(request: Request, session=Depends(get_session)):
                cid = f"{p_name}-main"
                comp = session.get_component(cid)
                if comp is None:
                    comp = session.mount_component(p_name, cid=cid)

                if hasattr(comp, "mount_async") and asyncio.iscoroutinefunction(
                    comp.mount_async
                ):
                    await comp.mount_async()

                comp_html = session.renderer.render_component(comp)

                # Auto-inject TimeTravelPanel for local development state tracing
                if config.live_reload or config.hrepl_enabled:
                    import hiccl.live_reload.time_travel  # noqa: F401

                    debug_cid = "time-travel-panel-main"
                    debug_comp = session.get_component(debug_cid)
                    if debug_comp is None:
                        debug_comp = session.mount_component(
                            "time-travel-panel", cid=debug_cid
                        )
                    debug_html = session.renderer.render_component(debug_comp)
                    comp_html += debug_html

                # Generate the navigation menu using DaisyUI navbar
                menu_html = ""
                if config.pages:
                    menu_html = (
                        '<ul class="menu menu-horizontal px-1 gap-2" hx-boost="true">'
                    )
                    seen_classes = set()
                    for route_path, route_cls in config.pages.items():
                        if route_cls in seen_classes:
                            continue
                        seen_classes.add(route_cls)

                        r_name = getattr(
                            route_cls, "_hiccl_component_name", route_cls.__name__
                        )
                        display_name = (
                            re.sub(r"(?<!^)(?=[A-Z])", " ", r_name).strip().title()
                        )

                        is_active = (request.url.path == route_path) or (
                            route_path != "/"
                            and request.url.path.startswith(route_path)
                        )
                        active_class = 'class="active"' if is_active else ""
                        menu_html += f'<li><a href="{route_path}" {active_class}>{display_name}</a></li>'
                    menu_html += "</ul>"

                # Execute layout callback to generate full HTML page
                html = config.layout(request, comp_html, menu_html, config)

                response = HTMLResponse(html)
                response.set_cookie(
                    config.session_cookie_name,
                    session.session_id,
                    httponly=True,
                    samesite="lax",
                    path="/",
                )
                return response

            return handler

        app.get(path, response_class=HTMLResponse)(
            make_handler(path, comp_cls, comp_name)
        )


def menu(*components: type[Component]) -> dict[str, type[Component]]:
    """Helper to register routes for multiple components and generate a menu.

    The first component in the list is automatically mapped to "/".
    Subsequent components are mapped to "/<kebab-case-component-name>".
    """
    import re

    pages = {}
    for i, cls in enumerate(components):
        comp_name = getattr(cls, "_hiccl_component_name", cls.__name__)
        kebab_name = re.sub(r"(?<!^)(?=[A-Z])", "-", comp_name).strip("-").lower()

        path = f"/{kebab_name}"
        pages[path] = cls

        if i == 0:
            pages["/"] = cls

    return pages


def run_dev(app: FastAPI, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start development server."""
    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=True)
