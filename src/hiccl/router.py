"""Hiccl Declarative Router — Signal-driven SPA routing component."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING
from hiccl.component import Component, server
from hiccl.signal import Signal

if TYPE_CHECKING:
    from hiccl.session import Session


class Router(Component):
    """Declarative, Signal-driven SPA Router Component for Hiccl."""

    def __init__(
        self,
        routes: dict[str, type[Component] | Callable[[], Any]],
        initial_path: str = "/",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.routes = routes
        self.current_path = Signal(initial_path)

    def navigate(self, path: str) -> None:
        """Programmatically navigate to a path."""
        if self.current_path.get() != path:
            self.current_path.set(path)

    @server
    def goto(self, path: str) -> None:
        """Server-side action action for htmx on_click handlers."""
        self.navigate(path)

    def render(self) -> Any:
        path = self.current_path.get()

        # Match exact route or fallback
        target = self.routes.get(path)
        if target is None:
            # Look for fallback
            target = self.routes.get("/") or (
                lambda: ["div", None, "404 Page Not Found"]
            )

        # If target is a subclass of Component, mount/instantiate it
        if isinstance(target, type) and issubclass(target, Component):
            comp_class = target
            comp_name = getattr(comp_class, "_hiccl_component_name", None)
            if not comp_name:
                import re

                comp_name = (
                    re.sub(r"(?<!^)(?=[A-Z])", "-", comp_class.__name__)
                    .strip("-")
                    .lower()
                )
                comp_class._hiccl_component_name = comp_name

            cid = f"router-sub-{comp_name}"

            if getattr(self, "_session", None) is not None:
                # Active web session context: mount the subcomponent
                session: Session = self._session
                sub_comp = session.get_component(cid)
                if sub_comp is None:
                    # Register class dynamically if missing
                    try:
                        session._registry.resolve(comp_name)
                    except ValueError:
                        session._registry.register(comp_name, comp_class)
                    sub_comp = session.mount_component(comp_name, cid=cid)
                # Render using the registry component html pipeline
                return [
                    "__fragment__",
                    None,
                    ["__raw__", None, session.renderer.render_component(sub_comp)],
                ]
            else:
                # Standalone fallback context (for isolated unit tests)
                instance = comp_class()
                instance._discovered_signals()
                return instance.render()

        # If it's a simple callback/Hiccup provider
        if callable(target):
            return target()

        return target
