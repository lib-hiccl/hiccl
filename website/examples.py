"""Live examples registration for the Hiccl website.

Imports all example component classes from ``examples/``, registers them
(including sub-components) in the website's shared ComponentRegistry,
and returns a ``pages`` dict that maps URL routes to top-level components.
"""

from __future__ import annotations

import importlib

from hiccl import ComponentRegistry, set_registry


def _import(module_path: str, *names: str):
    """Import specific names from a hyphenated module path."""
    mod = importlib.import_module(module_path)
    return tuple(getattr(mod, n) for n in names)


def register_examples(registry: ComponentRegistry) -> dict:
    """Register all example components into *registry* and return pages dict."""

    # ── Phase 1: set our registry as the global target ────────────────
    set_registry(registry)

    # ── Phase 2: simple examples (no @component, no set_registry) ─────
    from examples.counter.app import Counter
    from examples.chat.app import ChatRoom

    TwoClocks, ServerTimeDisplay = _import(
        "examples.two-clocks.app",
        "TwoClocks",
        "ServerTimeDisplay",
    )
    CryptoTrader, BtcPriceDisplay, PortfolioDisplay, CashBalanceDisplay = _import(
        "examples.csp-crypto-trader.app",
        "CryptoTrader",
        "BtcPriceDisplay",
        "PortfolioDisplay",
        "CashBalanceDisplay",
    )
    (BabashkaTerminal,) = _import(
        "examples.babashka.app",
        "BabashkaTerminal",
    )

    # Register simple examples + their sub-components
    registry.register("counter", Counter)
    registry.register("server-time-display", ServerTimeDisplay)
    registry.register("two-clocks", TwoClocks)
    registry.register("chat-room", ChatRoom)
    registry.register("babashka-terminal", BabashkaTerminal)
    registry.register("btc-price-display", BtcPriceDisplay)
    registry.register("portfolio-display", PortfolioDisplay)
    registry.register("cash-balance-display", CashBalanceDisplay)
    registry.register("crypto-trader", CryptoTrader)

    # ── Phase 3: @component examples (may call set_registry themselves) ─
    set_registry(registry)  # restore before each import batch

    from examples.time_travel_demo import (
        ColorCanvas,
        CounterBox,
        TimeTravelSandbox,
        TimeTravelTodo,
    )

    set_registry(registry)  # restore (time_travel_demo overrides it)

    from examples.datalog_web_demo import (
        DatalogEntityNavigator,
        DatalogFlattenLoader,
        DatalogPullVisualizer,
        DatalogQueryConsole,
        DatalogSidebar,
        DatalogTabContent,
        DatalogTabNav,
        DatalogWebDemo,
    )

    set_registry(registry)  # restore (datalog_web_demo overrides it)

    from examples.premium_showcase import (
        CspShowcase,
        PremiumShowcaseFrame,
        ReactiveSandbox,
        ReframeTodoDemo,
        SpecProfileCard,
        WildcardEventHub,
    )

    # ── Phase 4: manually register all @component classes ─────────────
    set_registry(registry)  # final restore

    # Time Travel sub-components
    registry.register("counter-box", CounterBox)
    registry.register("color-canvas", ColorCanvas)
    registry.register("time-travel-todo", TimeTravelTodo)
    registry.register("time-travel-sandbox", TimeTravelSandbox)

    # Datalog sub-components
    registry.register("datalog-sidebar", DatalogSidebar)
    registry.register("datalog-tab-nav", DatalogTabNav)
    registry.register("datalog-query-console", DatalogQueryConsole)
    registry.register("datalog-pull-visualizer", DatalogPullVisualizer)
    registry.register("datalog-entity-navigator", DatalogEntityNavigator)
    registry.register("datalog-flatten-loader", DatalogFlattenLoader)
    registry.register("datalog-tab-content", DatalogTabContent)
    registry.register("datalog-web-demo", DatalogWebDemo)

    # Premium Showcase sub-components
    registry.register("reactive-sandbox", ReactiveSandbox)
    registry.register("spec-profile-card", SpecProfileCard)
    registry.register("wildcard-event-hub", WildcardEventHub)
    registry.register("reframe-todo-demo", ReframeTodoDemo)
    registry.register("csp-showcase", CspShowcase)
    registry.register("premium-showcase-frame", PremiumShowcaseFrame)

    # ── Phase 5: return the pages dict ────────────────────────────────
    return {
        "/examples/counter": Counter,
        "/examples/two-clocks": TwoClocks,
        "/examples/chat": ChatRoom,
        "/examples/babashka": BabashkaTerminal,
        "/examples/csp-crypto-trader": CryptoTrader,
        "/examples/time-travel": TimeTravelSandbox,
        "/examples/datalog": DatalogWebDemo,
        "/examples/premium-showcase": PremiumShowcaseFrame,
    }
