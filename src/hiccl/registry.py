"""Hiccl ComponentRegistry — component registration and factory."""

from __future__ import annotations

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


def component(name: str):
    """Decorator: register a class as a named component."""

    def wrapper(cls):
        if _registry is not None:
            _registry.register(name, cls)
        cls._hiccl_component_name = name  # type: ignore[attr-defined]
        return cls

    return wrapper
