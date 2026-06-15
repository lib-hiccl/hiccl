"""Hiccl re-frame — Multi-User Isolated Unidirectional Data Flow System."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Callable

from hiccl.component import ActionRef, _current_rendering_component, _in_render
from hiccl.signal import ComputedSignal, batch


# Global ContextVar for the current active Session
_current_session: ContextVar[Any] = ContextVar("_current_session", default=None)

# Global registries for re-frame event and subscription handlers
_re_frame_initial_state: dict[str, Any] = {}
_re_frame_subs_registry: dict[str, Callable] = {}
_re_frame_events_registry: dict[str, tuple[Callable, dict[str, Any] | None]] = {}


def reg_state(initial_state: dict[str, Any]) -> None:
    """Register the global initial state dict for re-frame."""
    global _re_frame_initial_state
    _re_frame_initial_state = {**_re_frame_initial_state, **initial_state}


def reg_sub(name: str) -> Callable[[Callable], Callable]:
    """Decorator to register a subscription handler."""

    def decorator(fn: Callable) -> Callable:
        _re_frame_subs_registry[name] = fn
        return fn

    return decorator


def reg_event(
    name: str, spec: dict[str, Any] | None = None
) -> Callable[[Callable], Callable]:
    """Decorator to register an event handler with optional Spec validation schema."""

    def decorator(fn: Callable) -> Callable:
        _re_frame_events_registry[name] = (fn, spec)
        return fn

    return decorator


def subscribe(name: str, *args: Any) -> ComputedSignal[Any]:
    """Subscribe to a derived state from the session's re-frame DB."""
    session = _current_session.get()
    if session is None:
        raise RuntimeError(
            "subscribe can only be called within an active session context"
        )

    if name not in _re_frame_subs_registry:
        raise ValueError(f"Subscription '{name}' is not registered")

    cache_key = (name, args)
    if cache_key not in session._re_frame_subs:
        fn = _re_frame_subs_registry[name]
        # Create a ComputedSignal that re-runs the subscription handler when session._re_frame_db changes
        comp_sig = ComputedSignal(lambda: fn(session._re_frame_db.get(), *args))
        session._re_frame_subs[cache_key] = comp_sig

    comp_sig = session._re_frame_subs[cache_key]

    # Automatically watch the ComputedSignal for the current component
    comp = _current_rendering_component.get()
    if comp is not None:
        if not hasattr(comp, "_watched_subs"):
            comp._watched_subs = set()
        if not hasattr(comp, "_watched_subs_signals"):
            comp._watched_subs_signals = []

        if cache_key not in comp._watched_subs:
            comp._watched_subs.add(cache_key)
            comp._watched_subs_signals.append(comp_sig)
            from hiccl.signal import Effect

            def make_effect(sub_sig, comp_id):
                def watch():
                    sub_sig.get()
                    if session.on_signal_change:
                        session.on_signal_change(comp_id)

                return watch

            effect = Effect(make_effect(comp_sig, comp.component_id))
            comp._effects.append(effect)

    return comp_sig


def dispatch(name: str, *args: Any) -> Any:
    """Dispatch an event to trigger a re-frame side effect or DB update."""
    if _in_render.get():
        # Render context -> return a deferred ActionRef pointing to the component's _dispatch_event
        comp = _current_rendering_component.get()
        if comp is None:
            raise RuntimeError(
                "dispatch can only be called inside a component during render"
            )
        return ActionRef(
            component_id=comp.component_id,
            method_name="_dispatch_event",
            bound_args={"event_name": name, "event_args": args},
        )

    session = _current_session.get()
    if session is None:
        raise RuntimeError(
            "dispatch can only be called within an active session context"
        )

    if name not in _re_frame_events_registry:
        raise ValueError(f"Event '{name}' is not registered")

    handler, spec_dict = _re_frame_events_registry[name]

    # v0.4.1 Spec validation:
    if spec_dict and "args" in spec_dict:
        args_spec = spec_dict["args"]
        from hiccl.spec import Spec, SpecValidationError

        if isinstance(args_spec, list):
            errors = []
            for i, param_spec in enumerate(args_spec):
                if isinstance(param_spec, Spec) and i < len(args):
                    field_errors = param_spec.explain_data(args[i], path=[f"arg_{i}"])
                    if field_errors:
                        errors.extend(field_errors)
            if errors:
                raise SpecValidationError(errors)

    # Perform DB update in a batch to defer intermediate effect triggerings
    with batch():
        current_db = session._re_frame_db.get()
        new_db = handler(current_db, *args)
        if new_db is not None:
            session._re_frame_db.set(new_db)
