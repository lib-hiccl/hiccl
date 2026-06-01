"""Unit and integration tests for Phase 5a — HistorySignal and Time Travel Panel."""

from __future__ import annotations

import pytest
import copy
from hiccl.signal import HistorySignal, signal_with_history, Signal
from hiccl.session import Session
from hiccl.registry import ComponentRegistry
from hiccl.renderer import HiccupRenderer
from hiccl.live_reload.time_travel import TimeTravelPanel
from hiccl.component import Component


def test_history_signal_basic_flow():
    """Test basic set, undo, redo, and limit limits for HistorySignal."""
    sig = HistorySignal(10, max_snapshots=5)

    assert sig.get() == 10
    assert sig.history == [10]
    assert sig.history_index == 0
    assert not sig.can_undo()
    assert not sig.can_redo()

    # Set some values
    sig.set(20)
    sig.set(30)
    sig.set(40)

    assert sig.get() == 40
    assert sig.history == [10, 20, 30, 40]
    assert sig.history_index == 3
    assert sig.can_undo()
    assert not sig.can_redo()

    # Undo step by step
    sig.undo()
    assert sig.get() == 30
    assert sig.history_index == 2
    assert sig.can_undo()
    assert sig.can_redo()

    sig.undo()
    assert sig.get() == 20
    assert sig.history_index == 1

    sig.undo()
    assert sig.get() == 10
    assert sig.history_index == 0
    assert not sig.can_undo()
    assert sig.can_redo()

    # Undo at boundary is a no-op
    sig.undo()
    assert sig.get() == 10

    # Redo step by step
    sig.redo()
    assert sig.get() == 20
    assert sig.history_index == 1

    # Overwrite future history by setting a new value
    sig.set(25)
    assert sig.get() == 25
    assert sig.history == [10, 20, 25]
    assert sig.history_index == 2
    assert not sig.can_redo()


def test_history_signal_max_snapshots():
    """Test that max_snapshots limits the history queue length."""
    sig = signal_with_history(0, max_snapshots=3)

    # 4 additions
    sig.set(1)
    sig.set(2)
    sig.set(3)
    sig.set(4)

    # Since max_snapshots is 3, history is capped
    assert sig.get() == 4
    assert len(sig.history) == 3
    assert sig.history == [2, 3, 4]
    assert sig.history_index == 2

    # Verify we can only undo twice
    assert sig.can_undo()
    sig.undo()
    assert sig.get() == 3
    assert sig.can_undo()
    sig.undo()
    assert sig.get() == 2
    assert not sig.can_undo()


def test_history_signal_mutable_data_protection():
    """Test deepcopy/freeze snapshot protection on mutable dict/list states."""
    initial_data = {"count": 1, "items": [1, 2]}
    sig = HistorySignal(initial_data)

    # Set new dict
    new_data = {"count": 2, "items": [3, 4]}
    sig.set(new_data)

    # In-place modify the local dict
    new_data["count"] = 999
    new_data["items"].append(5)

    # Ensure HistorySignal inner value is NOT polluted by external in-place modifications
    assert sig.get()["count"] == 2
    assert sig.get()["items"] == [3, 4]

    # Verify history snapshot remains intact
    sig.undo()
    assert sig.get() == {"count": 1, "items": [1, 2]}


def test_history_signal_jump_to():
    """Test jumping directly to specific history indices."""
    sig = HistorySignal("a")
    sig.set("b")
    sig.set("c")

    assert sig.get() == "c"

    sig.jump_to(0)
    assert sig.get() == "a"
    assert sig.can_redo()

    sig.jump_to(2)
    assert sig.get() == "c"

    with pytest.raises(IndexError):
        sig.jump_to(5)


def test_session_history_signal_collection():
    """Test that Session automatically discovers HistorySignals from mounted components."""
    registry = ComponentRegistry()

    class MyTestComponent(Component):
        def __init__(self):
            super().__init__()
            self.normal_sig = Signal("normal")
            self.hist_sig = signal_with_history("hist_init")

        def render(self):
            return ["div", {}, self.normal_sig.get(), self.hist_sig.get()]

    registry.register("test-comp", MyTestComponent)
    renderer = HiccupRenderer()
    session = Session("sess-abc", registry, renderer)

    comp = session.mount_component("test-comp", cid="test-comp-1")

    # Verify that hist_sig is discovered but normal_sig is NOT
    assert "test-comp-1.hist_sig" in session._history_signals
    assert "test-comp-1.normal_sig" not in session._history_signals

    # Verify that the re-frame global DB is also tracked
    assert "@re-frame-db" in session._history_signals


def test_time_travel_panel_server_methods():
    """Test server actions of TimeTravelPanel in a mock session environment."""
    registry = ComponentRegistry()
    registry.register("time-travel-panel", TimeTravelPanel)

    class CounterComponent(Component):
        def __init__(self):
            super().__init__()
            self.count = signal_with_history(0)

    registry.register("counter", CounterComponent)
    renderer = HiccupRenderer()
    session = Session("sess-123", registry, renderer)

    # Mount components
    counter = session.mount_component("counter", cid="counter-1")
    panel = session.mount_component("time-travel-panel", cid="panel-main")

    # Set some values in counter HistorySignal
    counter.count.set(10)
    counter.count.set(20)

    assert counter.count.get() == 20
    assert counter.count.history_index == 2

    # Simulate Toggle Panel
    assert not panel.expanded.get()
    panel.toggle_expand()
    assert panel.expanded.get()

    # Simulate Undo Signal via Panel
    panel.undo_signal("counter-1.count")
    assert counter.count.get() == 10
    assert counter.count.history_index == 1

    # Simulate Redo Signal via Panel
    panel.redo_signal("counter-1.count")
    assert counter.count.get() == 20
    assert counter.count.history_index == 2

    # Simulate Jump To via Panel
    panel.jump_to_index("counter-1.count", "0")
    assert counter.count.get() == 0
    assert counter.count.history_index == 0


def test_multi_session_isolation():
    """Test that HistorySignal states and TimeTravel changes are completely isolated per Session."""
    registry = ComponentRegistry()

    class IsolatedComp(Component):
        def __init__(self):
            super().__init__()
            self.val = signal_with_history("start")

    registry.register("iso-comp", IsolatedComp)
    renderer = HiccupRenderer()

    session_a = Session("session-a", registry, renderer)
    session_b = Session("session-b", registry, renderer)

    comp_a = session_a.mount_component("iso-comp", cid="comp-x")
    comp_b = session_b.mount_component("iso-comp", cid="comp-x")

    # Mutate Session A
    comp_a.val.set("value-a1")
    comp_a.val.set("value-a2")

    # Mutate Session B
    comp_b.val.set("value-b1")

    # Verify distinct values
    assert comp_a.val.get() == "value-a2"
    assert comp_b.val.get() == "value-b1"

    # Verify history indexes are separate
    assert len(session_a._history_signals["comp-x.val"].history) == 3
    assert len(session_b._history_signals["comp-x.val"].history) == 2

    # Undo Session A, Session B remains intact
    comp_a.val.undo()
    assert comp_a.val.get() == "value-a1"
    assert comp_b.val.get() == "value-b1"
