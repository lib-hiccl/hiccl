"""Tests for hiccl.registry — ComponentRegistry, set_registry, component decorator."""

import pytest

from hiccl.component import Component
from hiccl.registry import ComponentRegistry, component, set_registry


class SimpleComponent(Component):
    def render(self):
        return ["div", None, "hello"]


class TestComponentRegistry:
    def test_register_and_resolve(self):
        reg = ComponentRegistry()
        reg.register("simple", SimpleComponent)
        cls = reg.resolve("simple")
        assert cls is SimpleComponent

    def test_resolve_not_found(self):
        reg = ComponentRegistry()
        with pytest.raises(ValueError, match="not registered"):
            reg.resolve("nonexistent")

    def test_create_instance(self):
        reg = ComponentRegistry()
        reg.register("simple", SimpleComponent)
        comp = reg.create("simple")
        assert isinstance(comp, SimpleComponent)
        assert comp.component_id.startswith("simplecomponent-")

    def test_create_with_props(self):
        reg = ComponentRegistry()
        reg.register("simple", SimpleComponent)
        comp = reg.create("simple")
        comp.key = "test-key"
        assert comp.key == "test-key"


class TestSetRegistryAndDecorator:
    def test_component_decorator(self):
        reg = ComponentRegistry()
        set_registry(reg)

        @component("my-widget")
        class MyWidget(Component):
            def render(self):
                return ["div", None, "widget"]

        assert reg.resolve("my-widget") is MyWidget

    def test_component_decorator_preserves_class(self):
        reg = ComponentRegistry()
        set_registry(reg)

        @component("preserved")
        class Preserved(Component):
            custom_attr = True

            def render(self):
                return []

        assert Preserved.custom_attr is True
        assert hasattr(Preserved, "_hiccl_component_name")
        assert Preserved._hiccl_component_name == "preserved"
