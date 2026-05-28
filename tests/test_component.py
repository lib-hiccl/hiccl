"""Tests for hiccl.component — Component base class and @server decorator."""

import pytest

from hiccl.component import Component, get_server_methods, server
from hiccl.registry import ComponentRegistry
from hiccl.signal import Signal


class TestServerDecorator:
    def test_marks_method(self):
        class MyComp(Component):
            @server
            def do_thing(self):
                pass

        comp = MyComp()
        methods = get_server_methods(comp)
        assert "do_thing" in methods

    def test_non_server_method_excluded(self):
        class MyComp(Component):
            def render(self):
                return []

            def helper(self):
                pass

        comp = MyComp()
        methods = get_server_methods(comp)
        assert "helper" not in methods

    def test_multiple_server_methods(self):
        class MyComp(Component):
            @server
            def action_a(self):
                pass

            @server
            def action_b(self):
                pass

        comp = MyComp()
        methods = get_server_methods(comp)
        assert "action_a" in methods
        assert "action_b" in methods


class TestComponent:
    def test_component_id_generated(self):
        comp = Component()
        assert comp.component_id.startswith("component-")

    def test_component_id_unique(self):
        a = Component()
        b = Component()
        assert a.component_id != b.component_id

    def test_render_not_implemented(self):
        comp = Component()
        with pytest.raises(NotImplementedError):
            comp.render()

    def test_discovered_signals(self):
        class Counter(Component):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.count = Signal(0)

        counter = Counter()
        counter._discovered_signals()
        assert "count" in counter._signals

    def test_props_set_signals(self):
        class Counter(Component):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.count = Signal(0)

        reg = ComponentRegistry()
        reg.register("counter", Counter)
        counter = reg.create("counter", count=42)
        assert counter.count.get() == 42

    def test_shared_signal_props_not_corrupted(self):
        class Child(Component):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.count = Signal(0)

        parent_signal = Signal(100)
        reg = ComponentRegistry()
        reg.register("child", Child)
        child = reg.create("child", count=parent_signal)

        # Verify the child's signal is exactly the parent's signal object
        assert child.count is parent_signal
        # Verify the value was not corrupted by self-referential .set()
        assert child.count.get() == 100

    def test_action_url(self):
        comp = Component()
        comp.component_id = "test-123"
        url = comp.action_url("increment")
        assert url == "/hiccl/action/test-123/increment"

    def test_mount_unmount(self):
        """mount/unmount default to no-op, should not raise."""
        comp = Component()
        comp.mount()
        comp.unmount()


class TestSubclass:
    def test_subclass_render(self):
        from hiccl.hiccup import button, div, h2

        class Counter(Component):
            def __init__(self):
                super().__init__()
                self.count = Signal(0)

            @server
            def increment(self):
                self.count.set(self.count.get() + 1)

            def render(self):
                return div(
                    {"class": "counter"},
                    h2(f"Count: {self.count.get()}"),
                    button({"hx-post": self.action_url("increment")}, "+1"),
                )

        counter = Counter()
        tree = counter.render()
        assert tree[0] == "div"
        assert tree[1] == {"class": "counter"}
        counter.increment()
        assert counter.count.get() == 1
