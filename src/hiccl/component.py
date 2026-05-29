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
        spec: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(component.component_id, name)
        self._component = component
        self._fn = fn
        self.spec = spec

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if _in_render.get():
            # Render context → return a new ActionRef with bound args
            bound = self._map_args(args, kwargs)
            return ActionRef(self.component_id, self.method_name, bound)

        # Transport context → execute the real method
        if self.spec:
            from hiccl.spec import Spec, SpecValidationError

            args_spec = self.spec.get("args")
            return_spec = self.spec.get("return")

            if args_spec:
                bound_args = self._map_args(args, kwargs)
                errors = []
                if isinstance(args_spec, dict):
                    for param_name, param_spec in args_spec.items():
                        if isinstance(param_spec, Spec):
                            val = bound_args.get(param_name)
                            field_errors = param_spec.explain_data(
                                val, path=[param_name]
                            )
                            if field_errors:
                                errors.extend(field_errors)
                elif isinstance(args_spec, Spec):
                    field_errors = args_spec.explain_data(bound_args)
                    if field_errors:
                        errors.extend(field_errors)

                if errors:
                    raise SpecValidationError(errors)

            res = self._fn(self._component, *args, **kwargs)

            if return_spec and isinstance(return_spec, Spec):
                return_spec.validate(res)

            return res

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

    def __init__(self, fn: Callable, spec: dict[str, Any] | None = None) -> None:
        self._fn = fn
        self._name = fn.__name__
        self.spec = spec
        # Mark the original function so reflection on the class still works
        setattr(self._fn, _SERVER_METHODS_ATTR, True)

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(
        self, obj: Any, objtype: type | None = None
    ) -> BoundAction | ServerActionDescriptor:
        if obj is None:
            return self
        return BoundAction(obj, self._fn, self._name, spec=self.spec)


# ---------------------------------------------------------------------------
# Public decorator & helper
# ---------------------------------------------------------------------------


def server(
    method: Callable | None = None,
    *,
    spec: dict[str, Any] | None = None,
) -> Any:
    """Mark a method as a server action.

    Can be used as @server, or as @server(spec=...).
    """
    if method is not None:
        return ServerActionDescriptor(method)

    def decorator(fn: Callable) -> ServerActionDescriptor:
        return ServerActionDescriptor(fn, spec=spec)

    return decorator


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


# ---------------------------------------------------------------------------
# Functional component primitives (use_signal, _make_func_component)
# ---------------------------------------------------------------------------

_current_rendering_component: ContextVar[Component | None] = ContextVar(
    "_current_rendering_component", default=None
)


def use_signal(initial: Any) -> Signal[Any]:
    """React-Hooks style local state hook for functional components."""
    comp = _current_rendering_component.get()
    if comp is None:
        raise RuntimeError(
            "use_signal can only be called inside a functional component during render"
        )

    idx = comp._hook_index
    comp._hook_index += 1

    if idx not in comp._hook_signals:
        from hiccl.signal import Effect  # local import to avoid cycles if any

        sig = Signal(initial)
        comp._hook_signals[idx] = sig
        comp._signals[f"hook_{idx}"] = sig

        # Automatically register watch effect if component is already mounted
        session = getattr(comp, "_session", None)
        if session:

            def make_effect(signal_obj, comp_id):
                def watch():
                    signal_obj.get()
                    if session.on_signal_change:
                        session.on_signal_change(comp_id)

                return watch

            effect = Effect(make_effect(sig, comp.component_id))
            comp._effects.append(effect)

    return comp._hook_signals[idx]


def _make_func_component(name: str, fn: Callable) -> type[Component]:
    """Wrap a pure function in a FuncComponent (Component subclass) adapter."""

    class FuncComponent(Component):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__()
            self._args = args
            self._kwargs = kwargs
            self._hook_index = 0
            self._hook_signals: dict[int, Signal[Any]] = {}
            self._fn = fn

            # Map positional and keyword args to the function's signature
            try:
                sig = inspect.signature(fn)
                bound = sig.bind_partial(*args, **kwargs)
                bound.apply_defaults()
                self._bound_props = bound.arguments
            except Exception:
                self._bound_props = kwargs.copy()

            self._discovered_signals()

        def _discovered_signals(self) -> None:
            super()._discovered_signals()
            # Sync bound props with any attributes set by pending props (e.g. from session)
            for k in list(self._bound_props.keys()):
                if hasattr(self, k):
                    val = getattr(self, k)
                    self._bound_props[k] = val
                    if isinstance(val, Signal):
                        self._signals[k] = val

        def render(self) -> Any:
            self._hook_index = 0
            token = _current_rendering_component.set(self)
            try:
                return self._fn(**self._bound_props)
            finally:
                _current_rendering_component.reset(token)

        @server
        def _dispatch_event(
            self, event_name: str, event_args: list | tuple = (), **kwargs: Any
        ) -> None:
            from hiccl.re_frame import dispatch
            from hiccl.spec import SpecValidationError

            actual_args = list(event_args)
            if kwargs:
                clean_kwargs = {
                    k: v
                    for k, v in kwargs.items()
                    if not k.startswith("hx-") and k not in ("event_name", "event_args")
                }
                actual_args.extend(clean_kwargs.values())
                self._submitted_values = clean_kwargs

            try:
                dispatch(event_name, *actual_args)
                self._last_spec_error = None
            except SpecValidationError as e:
                self._last_spec_error = e.explain_data[0]["pred"]

    FuncComponent.__name__ = fn.__name__
    FuncComponent.__doc__ = fn.__doc__
    FuncComponent._hiccl_component_name = name

    from hiccl.registry import _registry

    if _registry is not None:
        _registry.register(name, FuncComponent)

    return FuncComponent
