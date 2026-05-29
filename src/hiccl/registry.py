"""Hiccl ComponentRegistry — component registration and factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from hiccl.component import Component


class ComponentRegistry:
    """Registry mapping component names to their classes."""

    def __init__(self) -> None:
        self._components: dict[str, type[Component]] = {}

    def register(self, name: str, cls: type[Component]) -> None:
        self._components[name] = cls

    def resolve(self, name: str) -> type[Component]:
        if name not in self._components:
            raise ValueError(f"Component '{name}' not registered")
        return self._components[name]

    def create(self, name: str, **props) -> Component:
        cls = self.resolve(name)
        instance = cls(**props)
        instance._discovered_signals()
        return instance


_registry: ComponentRegistry | None = None


def set_registry(registry: ComponentRegistry) -> None:
    """Set the global registry (used by @component decorator)."""
    global _registry
    _registry = registry


def component(arg: str | Callable | None = None) -> Any:
    """Unified decorator to register a component (class or pure function)."""
    if callable(arg):
        # Direct function decorator: @component def my_func(...)
        from hiccl.component import _make_func_component

        return _make_func_component(arg.__name__.lower(), arg)

    # Factory decorator: @component("my-name") or @component()
    name = arg

    def decorator(cls_or_fn: Any) -> Any:
        if isinstance(cls_or_fn, type) and issubclass(cls_or_fn, Component):
            if _registry is not None and name is not None:
                _registry.register(name, cls_or_fn)
            if name is not None:
                cls_or_fn._hiccl_component_name = name
            return cls_or_fn
        else:
            from hiccl.component import _make_func_component

            actual_name = name or cls_or_fn.__name__.lower()
            return _make_func_component(actual_name, cls_or_fn)

    return decorator
