"""Hiccl reactive signal system — Signal, ComputedSignal, Effect, batch()."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Generic, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Dependency tracking context
# ---------------------------------------------------------------------------


class _Tracker:
    """Collects Signal dependencies during ComputedSignal/Effect execution."""

    def __init__(self) -> None:
        self.dependencies: list[Signal[Any]] = []
        self._seen: set[int] = set()

    def add_dependency(self, signal: Signal[Any]) -> None:
        sig_id = id(signal)
        if sig_id not in self._seen:
            self._seen.add(sig_id)
            self.dependencies.append(signal)


_current_tracker: ContextVar[_Tracker | None] = ContextVar("_tracker", default=None)

# ---------------------------------------------------------------------------
# Batch support
# ---------------------------------------------------------------------------

_batch_level: ContextVar[int] = ContextVar("_batch_level", default=0)
_pending_effects: set[Effect] = set()


def _get_node_depth(node: Any, visited: set[Any] | None = None) -> int:
    """Calculate the reactive dependency depth of a ComputedSignal or Effect node."""
    if visited is None:
        visited = set()
    if node in visited:
        return 0  # Break cycles
    visited.add(node)

    if isinstance(node, ComputedSignal):
        return (
            max((_get_node_depth(src, visited) for src in node._sources), default=0) + 1
        )
    elif isinstance(node, Effect):
        return max((_get_node_depth(dep, visited) for dep in node._deps), default=0) + 1
    return 0


def _topological_sort(effects: set[Effect]) -> list[Effect]:
    """Sort effects so that lower depth (fewer upstream dependencies) runs first."""
    return sorted(effects, key=lambda e: _get_node_depth(e))


@contextmanager
def batch() -> Generator[None, None, None]:
    """Batch multiple signal changes; effects fire once at the end."""
    token = _batch_level.set(_batch_level.get() + 1)
    try:
        yield
    finally:
        val = _batch_level.get() - 1
        _batch_level.reset(token)
        if val == 0:
            effects = _pending_effects.copy()
            _pending_effects.clear()
            for effect in _topological_sort(effects):
                effect._execute()


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


class Signal(Generic[T]):
    """Reactive value container. .get() registers dependency with current tracker."""

    def __init__(self, initial: T) -> None:
        self._value: T = initial
        self._version: int = 0
        self._dependents: set[ComputedSignal[Any] | Effect] = set()

    def get(self) -> T:
        tracker = _current_tracker.get()
        if tracker is not None:
            tracker.add_dependency(self)
        return self._value

    def set(self, value: T) -> None:
        if self._value == value:
            return
        self._value = value
        self._version += 1
        for dep in list(self._dependents):
            dep.invalidate()

    def __repr__(self) -> str:
        return f"Signal({self._value!r})"


# ---------------------------------------------------------------------------
# ComputedSignal
# ---------------------------------------------------------------------------


_NO_FALLBACK = object()


class ComputedSignal(Signal[T]):
    """Derived signal: lazily recomputes when source signals change."""

    def __init__(
        self,
        compute_fn: Callable[[], T],
        fallback: Any = _NO_FALLBACK,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._compute_fn = compute_fn
        self._dirty = True
        self._sources: list[Signal[Any]] = []
        self.fallback = fallback
        self.on_error = on_error
        super().__init__(None)  # type: ignore[arg-type]
        # Initial computation to set value and discover sources
        self._recompute()

    def get(self) -> T:
        if self._dirty:
            self._recompute()
        tracker = _current_tracker.get()
        if tracker is not None:
            tracker.add_dependency(self)
        return self._value

    def _recompute(self) -> None:
        # Clean up old subscriptions
        for src in self._sources:
            src._dependents.discard(self)
        self._sources.clear()

        tracker = _Tracker()
        token = _current_tracker.set(tracker)
        try:
            new_value = self._compute_fn()
        except Exception as e:
            if self.on_error is not None:
                try:
                    self.on_error(e)
                except Exception:
                    pass
            if self.fallback is not _NO_FALLBACK:
                new_value = self.fallback
            else:
                raise e
        finally:
            _current_tracker.reset(token)

        self._sources = tracker.dependencies
        for src in self._sources:
            src._dependents.add(self)

        old_value = self._value
        self._dirty = False
        if old_value != new_value:
            self._version += 1
        self._value = new_value

    def invalidate(self) -> None:
        self._dirty = True
        self._version += 1
        for dep in list(self._dependents):
            dep.invalidate()


# ---------------------------------------------------------------------------
# Effect
# ---------------------------------------------------------------------------


class Effect:
    """Side-effect executor: runs immediately on creation, re-runs when dependencies change."""

    def __init__(self, effect_fn: Callable[[], None]) -> None:
        self._effect_fn = effect_fn
        self._deps: list[Signal[Any]] = []
        self._disposed = False
        self._execute()

    def _execute(self) -> None:
        # Clean up old subscriptions
        for dep in self._deps:
            dep._dependents.discard(self)
        self._deps.clear()

        tracker = _Tracker()
        token = _current_tracker.set(tracker)
        try:
            self._effect_fn()
        except Exception as e:
            import asyncio
            from hiccl.eventbus import event_bus

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    event_bus.publish(
                        "hiccl.error.effect",
                        {"error": str(e), "exception": e, "effect": self},
                    )
                )
            except RuntimeError:
                pass
        finally:
            _current_tracker.reset(token)

        self._deps = tracker.dependencies
        for dep in self._deps:
            dep._dependents.add(self)

    def invalidate(self) -> None:
        if self._disposed:
            return
        if _batch_level.get() > 0:
            _pending_effects.add(self)
        else:
            self._execute()

    def dispose(self) -> None:
        self._disposed = True
        for dep in self._deps:
            dep._dependents.discard(self)
        self._deps.clear()
