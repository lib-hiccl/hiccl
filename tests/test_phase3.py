"""Tests for Phase 3 — pure function components, re-frame unidirectional flow, error boundary, and testing tools."""

import asyncio
import pytest

import hiccl
from hiccl import (
    component,
    use_signal,
    reg_state,
    reg_sub,
    reg_event,
    subscribe,
    dispatch,
    signal,
    computed,
    effect,
    Component,
    ComponentRegistry,
    Session,
    HiccupRenderer,
)
from hiccl.re_frame import _current_session
from hiccl.testing import (
    render_to_string,
    mock_server,
    assert_signal_changes,
    given_spec,
)
from hiccl.spec import integer, string, keys, SpecValidationError


# ---------------------------------------------------------------------------
# 1. Pure Function Components & use_signal Tests
# ---------------------------------------------------------------------------


def test_unified_decorator_registration():
    """Verify that @component works as a unified decorator for both classes and functions."""
    reg = ComponentRegistry()
    hiccl.registry._registry = reg

    # Class registration
    @component("test-class-comp")
    class ClassComp(Component):
        def render(self):
            return ["div", "class-content"]

    assert reg.resolve("test-class-comp") is ClassComp

    # Function registration (with custom name)
    @component("test-func-comp-named")
    def NamedFuncComp(initial_val=0):
        return ["div", str(initial_val)]

    assert issubclass(reg.resolve("test-func-comp-named"), Component)

    # Function registration (inferred name)
    @component
    def inferred_func_comp(initial_val=10):
        return ["span", str(initial_val)]

    assert issubclass(reg.resolve("inferred_func_comp"), Component)


def test_use_signal_persistence_and_positional_kwargs():
    """Verify use_signal returns index-stable Signal and handles args/kwargs correctly."""

    @component
    def mock_counter(start_count: int, prefix: str = "val"):
        sig = use_signal(start_count)
        return ["div", f"{prefix}:{sig.get()}"]

    comp_cls = mock_counter
    # Create with positional and keyword arguments
    comp = comp_cls(5, prefix="count")

    # 1. First render
    renderer = HiccupRenderer()
    html1 = renderer.render_component(comp)
    assert "count:5" in html1

    # Retrieve and modify the local use_signal
    local_sig = comp._hook_signals[0]
    local_sig.set(42)

    # 2. Second render (state is preserved)
    html2 = renderer.render_component(comp)
    assert "count:42" in html2


# ---------------------------------------------------------------------------
# 2. re-frame Unidirectional Flow & Session Isolation Tests
# ---------------------------------------------------------------------------


def test_re_frame_session_isolation_and_flow():
    """Verify that re-frame state and subscription cache are physically isolated per session."""
    # 1. Register initial state, subscriptions, and events globally
    reg_state({"count": 10})

    @reg_sub("app-count")
    def sub_count(db):
        return db.get("count", 0)

    @reg_event("inc-count")
    def event_inc(db, step=1):
        return {**db, "count": db.get("count", 0) + step}

    # 2. Create 2 isolated sessions
    reg = ComponentRegistry()
    renderer = HiccupRenderer()

    session1 = Session("sess-1", reg, renderer)
    session2 = Session("sess-2", reg, renderer)

    # Confirm initial states
    assert session1._re_frame_db.get() == {"count": 10}
    assert session2._re_frame_db.get() == {"count": 10}

    # Execute action in Session 1
    token1 = _current_session.set(session1)
    try:
        # Check subscription
        c1 = subscribe("app-count")
        assert c1.get() == 10
        # Dispatch event in session 1
        dispatch("inc-count", 5)
        assert c1.get() == 15
    finally:
        _current_session.reset(token1)

    # Confirm Session 2's db remained untouched (isolation guarantee!)
    token2 = _current_session.set(session2)
    try:
        c2 = subscribe("app-count")
        assert c2.get() == 10
        # Subscriptions cache must be separate
        assert session1._re_frame_subs != session2._re_frame_subs
    finally:
        _current_session.reset(token2)


def test_render_dispatch_deferred_action_ref():
    """Verify that calling dispatch during rendering returns an ActionRef."""

    @component
    def simple_btn():
        return ["button", {"on_click": dispatch("do-something", "arg1")}]

    reg = ComponentRegistry()
    hiccl.registry._registry = reg
    comp_cls = simple_btn
    comp = comp_cls()

    # Render component
    renderer = HiccupRenderer()
    html = renderer.render_component(comp)

    # The ActionRef was converted into standard HTMX attributes pointing to _dispatch_event
    assert "hx-post" in html
    assert "_dispatch_event" in html
    assert (
        'hx-vals="{&quot;event_name&quot;: &quot;do-something&quot;, &quot;event_args&quot;: [&quot;arg1&quot;]}"'
        in html
    )


# ---------------------------------------------------------------------------
# 3. Error Boundary Tests
# ---------------------------------------------------------------------------


def test_computed_signal_error_fallback_and_callback():
    """Verify ComputedSignal exception fallback and on_error handler."""
    base = signal(10)
    error_called = False

    def on_err(e):
        nonlocal error_called
        error_called = True

    # 1. With fallback and on_error
    derived = computed(lambda: 100 // base.get(), fallback=0, on_error=on_err)

    assert derived.get() == 10

    # Trigger zero division exception
    base.set(0)

    assert derived.get() == 0  # fallback value
    assert error_called is True

    # 2. No fallback (should propagate exception)
    base.set(10)
    derived_no_fallback = computed(lambda: 100 // base.get())
    assert derived_no_fallback.get() == 10

    # Trigger zero division exception
    base.set(0)
    with pytest.raises(ZeroDivisionError):
        derived_no_fallback.get()


@pytest.mark.asyncio
async def test_effect_error_boundary_eventbus_broadcasting():
    """Verify Effect exceptions are caught and broadcasted via EventBus."""
    from hiccl.eventbus import event_bus

    queue = asyncio.Queue()
    event_bus.subscribe("hiccl.error.effect", queue)

    err_sig = signal(1)

    # Create effect that will throw error on change
    def problematic_effect():
        val = err_sig.get()
        if val == 0:
            raise ValueError("Intentional effect failure")

    eff = effect(problematic_effect)

    # Trigger exception
    err_sig.set(0)

    # Wait for the broadcasted eventbus notification
    await asyncio.sleep(0.05)

    assert not queue.empty()
    msg = await queue.get()
    assert msg["topic"] == "hiccl.error.effect"
    assert "Intentional effect failure" in msg["data"]["error"]

    # Cleanup
    eff.dispose()
    event_bus.unsubscribe_all(queue)


# ---------------------------------------------------------------------------
# 4. hiccl.testing Tools & Hypothesis Strategy Bridge Tests
# ---------------------------------------------------------------------------


def test_snapshot_testing():
    """Verify render_to_string returns correct HTML string."""

    @component
    def simple_div(title):
        return ["div", {"class": "test-box"}, ["h1", title]]

    comp = simple_div("Hello World")
    html = render_to_string(comp)
    assert 'class="test-box"' in html
    assert "<h1>Hello World</h1>" in html


def test_mock_server_fixture():
    """Verify mock_server correctly mocks server actions on class components."""

    class ActionComp(Component):
        def __init__(self):
            super().__init__()
            self.val = signal(0)

        @hiccl.server
        def process_val(self, factor):
            self.val.set(100 * factor)
            return True

    comp = ActionComp()

    # 1. Normal execution
    comp.process_val(2)
    assert comp.val.get() == 200

    # 2. Mocked execution
    with mock_server(comp, "process_val", 999):
        # When called in render context, returns ActionRef.
        # When called directly, acts as the mock.
        res = comp.process_val(5)
        assert res == 999
        # Val remained unchanged because mock was executed instead
        assert comp.val.get() == 200


def test_assert_signal_changes_fixture():
    """Verify assert_signal_changes correctly tracks changes and verifies value."""
    sig = signal(1)

    with assert_signal_changes(sig, expected_value=42):
        sig.set(42)

    # Expect assertion error if signal doesn't change
    with pytest.raises(AssertionError, match="Expected signal to change"):
        with assert_signal_changes(sig):
            pass


def test_spec_validation_on_event_dispatch():
    """Verify Spec contracts are verified when dispatching re-frame events."""
    reg_state({"val": ""})

    # Configure string spec limit
    str_spec = string(min_len=3, max_len=10)

    @reg_event("update-val", spec={"args": [str_spec]})
    def handle_update(db, val):
        return {**db, "val": val}

    session = Session("sess-spec", ComponentRegistry(), HiccupRenderer())
    token = _current_session.set(session)
    try:
        # Invalid dispatch: too short
        with pytest.raises(SpecValidationError, match="len >= 3"):
            dispatch("update-val", "ab")

        # Valid dispatch
        dispatch("update-val", "abc")
        assert session._re_frame_db.get()["val"] == "abc"
    finally:
        _current_session.reset(token)


@given_spec(
    keys(
        req={
            "id": integer(gt=0),
            "name": string(min_len=2, max_len=15),
        }
    )
)
def test_hypothesis_spec_bridge_generative(user_dict):
    """Verify that given_spec correctly bridges Spec to Hypothesis strategy."""
    assert isinstance(user_dict["id"], int)
    assert user_dict["id"] > 0
    assert isinstance(user_dict["name"], str)
    assert 2 <= len(user_dict["name"]) <= 15


def test_dispatch_event_kwargs_mapping_and_validation():
    """Verify that _dispatch_event handles kwargs mapping and captures validation error."""
    reg_state({"items": []})

    str_spec = string(min_len=3, max_len=10)

    @reg_event("add-item", spec={"args": [str_spec]})
    def handle_add(db, val):
        return {**db, "items": db.get("items", []) + [val]}

    @component("test-comp")
    def TestComp():
        return "hello"

    session = Session("sess-dispatch", ComponentRegistry(), HiccupRenderer())
    token = _current_session.set(session)
    try:
        # Create an instance of dynamic FuncComponent
        comp_cls = TestComp
        comp = comp_cls()
        comp._session = session

        # 1. Valid dispatch with kwargs
        comp._dispatch_event(event_name="add-item", event_args=(), todo_text="hello")
        assert session._re_frame_db.get()["items"] == ["hello"]
        assert getattr(comp, "_last_spec_error", None) is None
        assert comp._submitted_values == {"todo_text": "hello"}

        # 2. Invalid dispatch (triggers SpecValidationError)
        comp._dispatch_event(event_name="add-item", event_args=(), todo_text="hi")
        # Should NOT raise, but capture the validation error predicate
        assert getattr(comp, "_last_spec_error", None) is not None
        assert "len >= 3" in getattr(comp, "_last_spec_error", "")
        assert comp._submitted_values == {"todo_text": "hi"}

    finally:
        _current_session.reset(token)


def test_subscription_reactive_dirty_marking():
    """Verify that changing a re-frame subscription automatically marks the component dirty."""
    reg_state({"count": 10})

    @reg_sub("count-val")
    def sub_count(db):
        return db.get("count", 0)

    @reg_event("inc-count")
    def handle_inc(db):
        return {**db, "count": db.get("count", 0) + 1}

    @component("sub-comp")
    def SubComp():
        val = subscribe("count-val").get()
        return f"value:{val}"

    # Setup session & scheduler
    registry = ComponentRegistry()
    registry.register("sub-comp", SubComp)

    session = Session("sess-sub-watch", registry, HiccupRenderer())

    dirty_components = []
    session.on_signal_change = lambda cid: dirty_components.append(cid)

    token = _current_session.set(session)
    try:
        # Mount and initially render the component
        comp = session.mount_component("sub-comp", cid="comp-1")
        session.renderer.render_component(comp)

        # At this point, the subscription is watched.
        # Verify that dispatching an event that changes the subscription marks the component dirty
        dispatch("inc-count")

        assert "comp-1" in dirty_components
    finally:
        _current_session.reset(token)


@pytest.mark.asyncio
async def test_event_bus_overlapping_wildcard_deduplication():
    """Verify that publishing an event matching multiple wildcard subscriptions for the same queue delivers it exactly once."""
    from hiccl.eventbus import event_bus

    queue = asyncio.Queue()
    try:
        # Subscribe the same queue to overlapping topics
        event_bus.subscribe("sport.*", queue)
        event_bus.subscribe("sport.#", queue)

        # Publish a message that matches both
        await event_bus.publish("sport.basketball", "slam-dunk")

        # Drain and assert exactly one message was delivered to the queue
        await asyncio.sleep(0.02)
        assert queue.qsize() == 1
        msg = queue.get_nowait()
        assert msg["data"] == "slam-dunk"
    finally:
        event_bus.unsubscribe_all(queue)


def test_websocket_transport_silent_dependency_binding_prevents_loop():
    """Verify that initial rendering in WS transport occurs before assigning on_signal_change,
    preventing infinite loops from render-phase signal modifications.
    """

    @component("loop-trigger-comp")
    class LoopTriggerComp(Component):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.val = signal(0)
            self.run_count = 0

        def render(self):
            self.run_count += 1
            if self.val.get() == 0:
                self.val.set(100)
            return ["div", str(self.val.get())]

    registry = ComponentRegistry()
    registry.register("loop-trigger-comp", LoopTriggerComp)
    renderer = HiccupRenderer()
    session = Session("sess-loop-test", registry, renderer)

    comp = session.mount_component("loop-trigger-comp", cid="comp-loop")

    from hiccl.scheduler import RenderScheduler

    scheduler = RenderScheduler()

    # Simulate WebSocket connection setup reordering:
    # 1. Force initial renders silently while session.on_signal_change is still None
    for c in list(session._components.values()):
        if not c._effects:
            session.renderer.render_component(c)

    # 2. Attach scheduler callback afterwards
    session.on_signal_change = scheduler.mark_dirty

    # Assert no loop was triggered and the scheduler did not receive any dirty events during initialization
    assert "comp-loop" not in scheduler._dirty

    # Confirm reactive flow still works normally for external post-init changes
    comp.val.set(200)
    assert "comp-loop" in scheduler._dirty


# ---------------------------------------------------------------------------
# 5. Granular Class & Function Unit Tests
# ---------------------------------------------------------------------------


def test_bound_action_map_args_unit():
    """Unit test for BoundAction._map_args across various function signatures."""
    from hiccl.component import BoundAction

    class DummyComp:
        component_id = "comp-dummy"

    comp = DummyComp()

    # 1. No arguments
    def func_no(self):
        pass

    ba_no = BoundAction(comp, func_no, "func_no")
    assert ba_no._map_args((), {}) == {}

    # 2. Positional and keyword mapping
    def func_pos(self, x, y):
        pass

    ba_pos = BoundAction(comp, func_pos, "func_pos")
    assert ba_pos._map_args((10,), {"y": 20}) == {"x": 10, "y": 20}
    assert ba_pos._map_args((), {"x": 5, "y": 15}) == {"x": 5, "y": 15}

    # 3. Varargs and kwargs mapping
    def func_var(self, head, *args, tail=1, **kwargs):
        pass

    ba_var = BoundAction(comp, func_var, "func_var")
    assert ba_var._map_args((100, 200), {"tail": 5, "z": 9}) == {
        "head": 100,
        "args": 200,
        "tail": 5,
        "z": 9,
    }


def test_use_signal_outside_render_throws_unit():
    """Unit test: use_signal called outside active component render context must raise RuntimeError."""
    from hiccl.component import use_signal

    with pytest.raises(
        RuntimeError,
        match="use_signal can only be called inside a functional component",
    ):
        use_signal("error-state")


def test_make_func_component_attributes_unit():
    """Unit test: _make_func_component dynamic class generation metadata and signature default values."""
    from hiccl.component import _make_func_component

    def custom_func(x, factor=10):
        """Standard docstring."""
        return ["div", str(x * factor)]

    comp_cls = _make_func_component("custom-func-comp", custom_func)

    # Validate metadata forwarding
    assert comp_cls.__name__ == "custom_func"
    assert comp_cls.__doc__ == "Standard docstring."
    assert comp_cls._hiccl_component_name == "custom-func-comp"

    # Validate signature inspection and prop default binding
    inst = comp_cls(5)
    assert inst._bound_props == {"x": 5, "factor": 10}


def test_re_frame_registration_edge_cases_unit():
    """Unit test: re_frame decorator registries preserve original callables and allow overrides."""
    from hiccl.re_frame import (
        reg_sub,
        reg_event,
        _re_frame_subs_registry,
        _re_frame_events_registry,
    )

    # 1. Registration overrides for subscriptions
    @reg_sub("sub-unit-test")
    def sub_orig(db):
        return "orig"

    assert sub_orig(None) == "orig"
    assert _re_frame_subs_registry["sub-unit-test"] is sub_orig

    @reg_sub("sub-unit-test")
    def sub_override(db):
        return "override"

    assert _re_frame_subs_registry["sub-unit-test"] is sub_override

    # 2. Event registration
    @reg_event("event-unit-test")
    def event_orig(db):
        return db

    assert _re_frame_events_registry["event-unit-test"][0] is event_orig


def test_subscribe_dispatch_no_session_raises_unit():
    """Unit test: subscribe and dispatch must raise RuntimeError when active session context is missing."""
    from hiccl.re_frame import subscribe, dispatch

    with pytest.raises(
        RuntimeError,
        match="subscribe can only be called within an active session context",
    ):
        subscribe("app-db-sub")

    with pytest.raises(
        RuntimeError,
        match="dispatch can only be called within an active session context",
    ):
        dispatch("app-db-event")


def test_subscribe_not_found_raises_unit():
    """Unit test: subscribe to an unregistered sub name must raise ValueError."""
    from hiccl import Session, ComponentRegistry, HiccupRenderer
    from hiccl.re_frame import subscribe, _current_session

    session = Session("sess-unit-sub", ComponentRegistry(), HiccupRenderer())
    token = _current_session.set(session)
    try:
        with pytest.raises(
            ValueError, match="Subscription 'ghost-sub-name' is not registered"
        ):
            subscribe("ghost-sub-name")
    finally:
        _current_session.reset(token)


def test_dispatch_in_render_returns_action_ref_unit():
    """Unit test: dispatch inside rendering context returns ActionRef with correct event envelope bindings."""
    from hiccl.re_frame import dispatch, _current_session
    from hiccl.component import _in_render, _current_rendering_component, ActionRef

    @component("test-disp-render-comp")
    def render_comp():
        return "ok"

    registry = ComponentRegistry()
    registry.register("test-disp-render-comp", render_comp)
    session = Session("sess-disp-unit", registry, HiccupRenderer())
    comp_inst = session.mount_component("test-disp-render-comp", cid="comp-u")

    token_sess = _current_session.set(session)
    token_comp = _current_rendering_component.set(comp_inst)
    token_render = _in_render.set(True)
    try:
        action_ref = dispatch("add-item-event", "arg1", "arg2")
        assert isinstance(action_ref, ActionRef)
        assert action_ref.component_id == "comp-u"
        assert action_ref.method_name == "_dispatch_event"
        assert action_ref.bound_args == {
            "event_name": "add-item-event",
            "event_args": ("arg1", "arg2"),
        }
    finally:
        _in_render.reset(token_render)
        _current_rendering_component.reset(token_comp)
        _current_session.reset(token_sess)


def test_assert_signal_changes_assertion_errors_unit():
    """Unit test: assert_signal_changes raises AssertionError when expected changes or values are not matched."""
    from hiccl.signal import Signal
    from hiccl.testing import assert_signal_changes

    sig = Signal("initial")

    # 1. Expect failure when signal is not changed at all
    with pytest.raises(AssertionError, match="Expected signal to change"):
        with assert_signal_changes(sig):
            pass

    # 2. Expect failure when signal value does not match expected_value
    with pytest.raises(
        AssertionError, match="Expected signal to become expected-match"
    ):
        with assert_signal_changes(sig, expected_value="expected-match"):
            sig.set("mismatched-value")
