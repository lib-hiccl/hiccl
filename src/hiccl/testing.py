"""Hiccl testing tools and Hypothesis strategy bridge."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable

from hiccl.component import Component
from hiccl.signal import Signal
from hiccl.spec import (
    Spec,
    NilSpec,
    AnySpec,
    NumberSpec,
    StringSpec,
    BooleanSpec,
    CollOfSpec,
    KeysSpec,
    AndSpec,
    OrSpec,
    PredicateSpec,
)


# Optional Hypothesis import
try:
    import hypothesis
    import hypothesis.strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False


def render_to_string(component: Component) -> str:
    """Render a component instance to its serialized HTML string without starting a server."""
    from hiccl.renderer import HiccupRenderer

    renderer = HiccupRenderer()
    return renderer.render_component(component)


@contextmanager
def mock_server(component: Component, method_name: str, mock_value_or_fn: Any) -> Any:
    """Mock a @server action method on a component instance."""
    if not callable(mock_value_or_fn):

        def mock_fn(*a: Any, **kw: Any) -> Any:
            return mock_value_or_fn
    else:
        mock_fn = mock_value_or_fn

    # Set the server marker attribute so get_server_methods reflection still recognizes it
    setattr(mock_fn, "_hiccl_server_method", True)

    # Override on the instance dict
    component.__dict__[method_name] = mock_fn
    try:
        yield
    finally:
        component.__dict__.pop(method_name, None)


@contextmanager
def assert_signal_changes(sig: Signal[Any], expected_value: Any = None) -> Any:
    """Assert that a signal value changes during the block execution."""
    changed = False
    original_set = sig.set

    def wrapped_set(val: Any) -> None:
        nonlocal changed
        changed = True
        original_set(val)

    sig.set = wrapped_set
    try:
        yield
        assert changed, "Expected signal to change, but it did not"
        if expected_value is not None:
            assert sig.get() == expected_value, (
                f"Expected signal to become {expected_value}, but got {sig.get()}"
            )
    finally:
        sig.set = original_set


# ---------------------------------------------------------------------------
# Hypothesis Spec Strategy Bridge
# ---------------------------------------------------------------------------


def spec_to_strategy(spec_obj: Spec) -> Any:
    """Convert a hiccl.spec validator Spec to a Hypothesis search strategy."""
    if not HAS_HYPOTHESIS:
        raise ImportError(
            "Hypothesis is required to use generation-based testing. Run 'pip install hypothesis'."
        )

    if isinstance(spec_obj, NilSpec):
        return st.none()
    elif isinstance(spec_obj, AnySpec):
        return st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.booleans(),
        )
    elif isinstance(spec_obj, NumberSpec):
        if spec_obj.is_int:
            min_v = spec_obj.gte
            if spec_obj.gt is not None:
                min_v = max(min_v or spec_obj.gt, spec_obj.gt + 1)
            max_v = spec_obj.lte
            if spec_obj.lt is not None:
                max_v = min(max_v or spec_obj.lt, spec_obj.lt - 1)
            return st.integers(min_value=min_v, max_value=max_v)
        else:
            min_v = spec_obj.gte if spec_obj.gte is not None else spec_obj.gt
            max_v = spec_obj.lte if spec_obj.lte is not None else spec_obj.lt
            exclude_min = spec_obj.gt is not None and spec_obj.gte is None
            exclude_max = spec_obj.lt is not None and spec_obj.lte is None
            return st.floats(
                min_value=min_v,
                max_value=max_v,
                exclude_min=exclude_min,
                exclude_max=exclude_max,
                allow_nan=False,
                allow_infinity=False,
            )
    elif isinstance(spec_obj, StringSpec):
        if spec_obj.pattern:
            regex_str = spec_obj.pattern.pattern
            return st.from_regex(regex_str)
        else:
            return st.text(min_size=spec_obj.min_len or 0, max_size=spec_obj.max_len)
    elif isinstance(spec_obj, BooleanSpec):
        return st.booleans()
    elif isinstance(spec_obj, CollOfSpec):
        return st.lists(
            spec_to_strategy(spec_obj.element_spec),
            min_size=spec_obj.min_len or 0,
            max_size=spec_obj.max_len,
        )
    elif isinstance(spec_obj, KeysSpec):
        req_strats = {k: spec_to_strategy(s) for k, s in spec_obj.req.items()}
        opt_strats = {k: spec_to_strategy(s) for k, s in spec_obj.opt.items()}
        return st.fixed_dictionaries(req_strats, optional=opt_strats)
    elif isinstance(spec_obj, AndSpec):
        base_strategy = spec_to_strategy(spec_obj.specs[0])
        return base_strategy.filter(lambda x: spec_obj.valid(x))
    elif isinstance(spec_obj, OrSpec):
        return st.one_of(*(spec_to_strategy(s) for s in spec_obj.specs.values()))
    elif isinstance(spec_obj, PredicateSpec):
        return st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.booleans(),
        ).filter(spec_obj.predicate)
    else:
        return st.just(None)


def given_spec(spec_obj: Spec) -> Callable:
    """Decorator to generate test parameters from a hiccl.spec validator via Hypothesis."""
    if not HAS_HYPOTHESIS:
        raise ImportError("Hypothesis is required to use generation-based testing.")
    strategy = spec_to_strategy(spec_obj)
    return hypothesis.given(strategy)
