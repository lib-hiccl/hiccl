"""Tests for hiccl.signal — Signal, ComputedSignal, Effect, batch."""

from hiccl.signal import ComputedSignal, Effect, Signal, batch

# ---------------------------------------------------------------------------
# Signal basics
# ---------------------------------------------------------------------------


class TestSignal:
    def test_initial_value(self):
        s = Signal(42)
        assert s.get() == 42

    def test_set_value(self):
        s = Signal(0)
        s.set(10)
        assert s.get() == 10

    def test_set_same_value_noop(self):
        s = Signal(5)
        old_version = s._version
        s.set(5)
        assert s._version == old_version

    def test_version_increments(self):
        s = Signal(0)
        assert s._version == 0
        s.set(1)
        assert s._version == 1
        s.set(2)
        assert s._version == 2

    def test_get_without_tracker(self):
        """get() should work fine without any tracker context."""
        s = Signal("hello")
        assert s.get() == "hello"

    def test_repr(self):
        s = Signal(42)
        assert repr(s) == "Signal(42)"


# ---------------------------------------------------------------------------
# ComputedSignal
# ---------------------------------------------------------------------------


class TestComputedSignal:
    def test_basic_derived(self):
        a = Signal(2)
        b = Signal(3)
        total = ComputedSignal(lambda: a.get() + b.get())
        assert total.get() == 5

    def test_lazy_recompute(self):
        a = Signal(1)
        compute_count = 0

        def compute():
            nonlocal compute_count
            compute_count += 1
            return a.get() * 2

        c = ComputedSignal(compute)
        assert c.get() == 2
        assert compute_count == 1

        # Set same value — no recompute needed
        a.set(1)
        # Accessing get triggers check but value is same
        assert c.get() == 2

    def test_reacts_to_source_change(self):
        a = Signal(10)
        doubled = ComputedSignal(lambda: a.get() * 2)
        assert doubled.get() == 20
        a.set(15)
        assert doubled.get() == 30

    def test_chained_computed(self):
        a = Signal(1)
        b = ComputedSignal(lambda: a.get() + 1)
        c = ComputedSignal(lambda: b.get() * 2)
        assert c.get() == 4  # (1+1)*2
        a.set(3)
        assert c.get() == 8  # (3+1)*2


# ---------------------------------------------------------------------------
# Effect
# ---------------------------------------------------------------------------


class TestEffect:
    def test_runs_on_creation(self):
        s = Signal(0)
        results = []
        Effect(lambda: results.append(s.get()))
        assert results == [0]

    def test_reacts_to_change(self):
        s = Signal(0)
        results = []
        Effect(lambda: results.append(s.get()))
        assert results == [0]
        s.set(1)
        assert results == [0, 1]
        s.set(2)
        assert results == [0, 1, 2]

    def test_dispose_stops_reactions(self):
        s = Signal(0)
        results = []
        eff = Effect(lambda: results.append(s.get()))
        assert results == [0]
        eff.dispose()
        s.set(1)
        assert results == [0]  # No update after dispose

    def test_multiple_deps(self):
        a = Signal(1)
        b = Signal(2)
        results = []
        Effect(lambda: results.append(a.get() + b.get()))
        assert results == [3]
        a.set(10)
        assert results == [3, 12]
        b.set(20)
        assert results == [3, 12, 30]

    def test_dynamic_deps(self):
        """Effect with conditional dep tracking."""
        flag = Signal(True)
        a = Signal("A")
        b = Signal("B")
        results = []

        def tracked():
            results.append(a.get() if flag.get() else b.get())

        Effect(tracked)
        assert results == ["A"]

        # Changing b should NOT trigger (b is not tracked when flag=True)
        b.set("B2")
        assert results == ["A"]

        # Switch flag to False — now b is tracked
        flag.set(False)
        assert results == ["A", "B2"]

        # Now changing a should NOT trigger
        a.set("A2")
        # But b changes should
        b.set("B3")
        assert results == ["A", "B2", "B3"]


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


class TestBatch:
    def test_batch_defers_effects(self):
        s = Signal(0)
        results = []
        Effect(lambda: results.append(s.get()))
        assert results == [0]

        with batch():
            s.set(1)
            s.set(2)
            s.set(3)
        # Effect fires once with the final value
        assert results == [0, 3]

    def test_batch_multiple_signals(self):
        a = Signal(1)
        b = Signal(2)
        results = []
        Effect(lambda: results.append(a.get() + b.get()))
        assert results == [3]

        with batch():
            a.set(10)
            b.set(20)
        assert results == [3, 30]


# ---------------------------------------------------------------------------
# Integration: Signal + ComputedSignal + Effect
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_signal_computed_effect_chain(self):
        base = Signal(1)
        doubled = ComputedSignal(lambda: base.get() * 2)
        results = []
        Effect(lambda: results.append(doubled.get()))
        assert results == [2]

        base.set(5)
        assert results == [2, 10]

    def test_effect_with_computed_dep(self):
        a = Signal(3)
        b = ComputedSignal(lambda: a.get() ** 2)
        results = []
        Effect(lambda: results.append(b.get()))
        assert results == [9]
        a.set(4)
        assert results == [9, 16]


class TestTopologicalSort:
    def test_topological_order_batch(self):
        """Verify that effects in a batch are executed in topological (depth) order."""
        a = Signal(1)
        # b depends on a
        b = ComputedSignal(lambda: a.get() * 2)

        order = []
        # Effect 1 reads a directly (depth 1)
        Effect(lambda: (order.append("A"), a.get()))
        # Effect 2 reads b (depth 2)
        Effect(lambda: (order.append("B"), b.get()))

        order.clear()
        # In batch, change a
        with batch():
            a.set(10)

        # Because A is depth 1 and B is depth 2, Effect A must run before Effect B
        assert order == ["A", "B"]
