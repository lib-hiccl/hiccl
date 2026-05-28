"""Tests for hiccl.session — Session management."""

from hiccl.component import Component, server
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.session import Session, _sessions
from hiccl.signal import Signal


class SimpleCounter(Component):
    def __init__(self):
        super().__init__()
        self.count = Signal(0)

    @server
    def increment(self):
        self.count.set(self.count.get() + 1)

    def render(self):
        return ["div", None, str(self.count.get())]


class TestSession:
    def setup_method(self):
        self.registry = ComponentRegistry()
        self.registry.register("counter", SimpleCounter)
        self.renderer = HiccupRenderer()

    def test_create_session(self):
        session = Session("sess-1", self.registry, self.renderer)
        assert session.session_id == "sess-1"

    def test_mount_component(self):
        session = Session("sess-2", self.registry, self.renderer)
        comp = session.mount_component("counter")
        assert comp is not None
        assert comp.count.get() == 0

    def test_mount_with_custom_id(self):
        session = Session("sess-3", self.registry, self.renderer)
        comp = session.mount_component("counter", cid="my-counter")
        assert comp.component_id == "my-counter"

    def test_get_component(self):
        session = Session("sess-4", self.registry, self.renderer)
        comp = session.mount_component("counter")
        found = session.get_component(comp.component_id)
        assert found is comp

    def test_get_component_not_found(self):
        session = Session("sess-5", self.registry, self.renderer)
        assert session.get_component("nonexistent") is None

    def test_dispose(self):
        session = Session("sess-6", self.registry, self.renderer)
        comp = session.mount_component("counter")
        session.dispose()
        assert session.get_component(comp.component_id) is None

    def test_on_signal_change_callback(self):
        changes = []
        session = Session("sess-7", self.registry, self.renderer)
        session.on_signal_change = lambda cid: changes.append(cid)
        comp = session.mount_component("counter")
        comp.increment()
        assert len(changes) > 0
        assert comp.component_id in changes

    def test_render_after_action(self):
        session = Session("sess-8", self.registry, self.renderer)
        comp = session.mount_component("counter")
        html = session.renderer.render_component(comp)
        assert "0" in html
        comp.increment()
        html = session.renderer.render_component(comp)
        assert "1" in html
