"""Hiccl Component base class, @server decorator, and ActionRef system."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from hiccl.signal import Signal

_SERVER_METHODS_ATTR = "_hiccl_server_method"

# ---------------------------------------------------------------------------
# Render context flag
# ---------------------------------------------------------------------------

_in_render: ContextVar[bool] = ContextVar("_in_render", default=False)
"""When True, @server methods accessed during render() return ActionRef
instead of executing.  Set by render_component() in the renderer."""


# ---------------------------------------------------------------------------
# ActionRef — deferred action binding for on_* attributes
# ---------------------------------------------------------------------------


class ActionRef:
    """Represents a deferred server-action binding.

    Created during render when the user writes:
        button({"on_click": self.increment}, "+1")
        button({"on_click": self.increment(5)}, "+5")

    The autobind traversal converts ActionRef → htmx attributes.
    """

    def __init__(
        self,
        component_id: str,
        method_name: str,
        bound_args: dict[str, Any] | None = None,
    ) -> None:
        self.component_id = component_id
        self.method_name = method_name
        self.bound_args: dict[str, Any] = bound_args or {}

    def __repr__(self) -> str:
        args = f", bound_args={self.bound_args!r}" if self.bound_args else ""
        return f"ActionRef({self.method_name!r}{args})"


# ---------------------------------------------------------------------------
# BoundAction — descriptor return value, context-aware callable
# ---------------------------------------------------------------------------


class BoundAction(ActionRef):
    """Bound server action returned by ``ServerActionDescriptor.__get__``.

    Render context (``_in_render is True``):
        self.method        → the BoundAction itself (is-an ActionRef, zero args)
        self.method(5)     → returns ActionRef(component_id, name, {"step": 5})

    Transport context (``_in_render is False``):
        self.method(**body) → actually executes the underlying function
    """

    # Class-level flag so that ``get_server_methods`` reflection finds it
    _hiccl_server_method: bool = True

    def __init__(
        self,
        component: Component,
        fn: Callable,
        name: str,
    ) -> None:
        super().__init__(component.component_id, name)
        self._component = component
        self._fn = fn

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if _in_render.get():
            # Render context → return a new ActionRef with bound args
            bound = self._map_args(args, kwargs)
            return ActionRef(self.component_id, self.method_name, bound)
        # Transport context → execute the real method
        return self._fn(self._component, *args, **kwargs)

    # -- helpers -----------------------------------------------------------

    def _map_args(self, args: tuple, kwargs: dict) -> dict[str, Any]:
        """Map positional / keyword args to named params via signature inspection."""
        try:
            sig = inspect.signature(self._fn)
            params = [p for p in sig.parameters if p != "self"]
        except (ValueError, TypeError):
            params = []

        bound: dict[str, Any] = {}
        for i, arg in enumerate(args):
            key = params[i] if i < len(params) else f"_arg{i}"
            bound[key] = arg
        bound.update(kwargs)
        return bound

    def __repr__(self) -> str:
        return f"BoundAction({self.method_name!r})"


# ---------------------------------------------------------------------------
# ServerActionDescriptor — replaces @server-decorated methods on the class
# ---------------------------------------------------------------------------


class ServerActionDescriptor:
    """Non-data descriptor that returns a ``BoundAction`` on instance access.

    Enables:
        self.increment  → BoundAction (usable directly as on_* value)
        self.increment(5) → ActionRef with pre-bound args  (render context)
        self.increment(step=5) → same
    """

    def __init__(self, fn: Callable) -> None:
        self._fn = fn
        self._name = fn.__name__
        # Mark the original function so reflection on the class still works
        setattr(self._fn, _SERVER_METHODS_ATTR, True)

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(
        self, obj: Any, objtype: type | None = None
    ) -> BoundAction | ServerActionDescriptor:
        if obj is None:
            return self
        return BoundAction(obj, self._fn, self._name)


# ---------------------------------------------------------------------------
# Public decorator & helper
# ---------------------------------------------------------------------------


def server(method: Callable) -> ServerActionDescriptor:
    """Mark a method as a server action.

    Replaces the method with a ``ServerActionDescriptor`` so that:

    * In ``render()``: ``self.method`` / ``self.method(args)`` returns
      an ``ActionRef`` (deferred binding for ``on_*`` attributes).
    * In transport context: the method executes normally.
    """
    return ServerActionDescriptor(method)


def get_server_methods(cls_or_instance: Any) -> dict[str, Callable]:
    """Return all ``@server`` methods on *cls_or_instance*.

    Works with both the old marker-based ``@server`` and the new descriptor.
    """
    methods: dict[str, Callable] = {}
    for name in dir(cls_or_instance):
        try:
            attr = getattr(cls_or_instance, name, None)
        except Exception:
            continue
        if callable(attr) and getattr(attr, _SERVER_METHODS_ATTR, False):
            methods[name] = attr
    return methods


# ---------------------------------------------------------------------------
# Component base class
# ---------------------------------------------------------------------------


class Component:
    """UI component base class.  Subclasses define signals and ``render()``."""

    component_id: str
    key: str | None = None
    topics: list[str] = []  # EventBus topics this component subscribes to

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original_init = cls.__init__

        def wrapped_init(self, *args, **init_kwargs):
            is_outermost = not hasattr(self, "_in_wrapped_init")
            if is_outermost:
                self._in_wrapped_init = True
            try:
                original_init(self, *args, **init_kwargs)
            finally:
                if is_outermost:
                    try:
                        delattr(self, "_in_wrapped_init")
                    except AttributeError:
                        pass
            if is_outermost:
                self._discovered_signals()

        cls.__init__ = wrapped_init

    def __init__(self, **props: Any) -> None:
        self.component_id = f"{self.__class__.__name__.lower()}-{uuid.uuid4().hex[:8]}"
        self._signals: dict[str, Signal[Any]] = {}
        self._effects: list[Any] = []
        # Store props for later initialization
        self._pending_props = props

    def _discovered_signals(self) -> None:
        """Collect all Signal instances from the component.

        Should be called after the subclass __init__ has set up all signals.
        """
        if getattr(self, "_signals_discovered", False):
            return
        self._signals_discovered = True

        for name in dir(self):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(self, name, None)
            except Exception:
                continue
            if isinstance(attr, Signal):
                self._signals[name] = attr

        # Apply any pending props
        if hasattr(self, "_pending_props"):
            for k, v in self._pending_props.items():
                if isinstance(v, Signal):
                    self._signals[k] = v
                    setattr(self, k, v)
                elif k in self._signals:
                    self._signals[k].set(v)
                elif hasattr(self, k):
                    setattr(self, k, v)
            del self._pending_props

    def render(self) -> list:
        """Return a Hiccup tree. Must be overridden by subclasses."""
        raise NotImplementedError

    def mount(self) -> None:
        """Called when the component is mounted to a session."""
        pass

    def unmount(self) -> None:
        """Called when the component is removed from a session."""
        pass

    def on_broadcast(self, topic: str) -> None:
        """Called when an EventBus message arrives for a subscribed topic."""
        pass

    def action_url(self, method_name: str) -> str:
        """Return the URL for triggering a server action via HTTP."""
        return f"/hiccl/action/{self.component_id}/{method_name}"
