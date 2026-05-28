"""Hiccl — Reactive Multi-Tier Web Framework."""

from hiccl.app import (
    HicclConfig,
    create_hiccl_app,
    run_dev,
    menu,
    hiccl_default_layout,
    hiccl_card_layout,
    hiccl_raw_layout,
)
from hiccl.component import ActionRef, BoundAction, Component, server
from hiccl.eventbus import EventBus, event_bus
from hiccl.hiccup import (
    a,
    br_,
    button,
    div,
    footer,
    form,
    fragment,
    h1,
    h2,
    h3,
    header,
    hr_,
    img,
    input_,
    label,
    li,
    main,
    nav,
    ol,
    option,
    p,
    raw,
    section,
    select,
    span,
    table,
    tbody,
    td,
    textarea,
    th,
    thead,
    tr,
    ul,
)
from hiccl.registry import ComponentRegistry, component, set_registry
from hiccl.renderer import HiccupRenderer, autobind
from hiccl.scheduler import RenderScheduler
from hiccl.session import Session
from hiccl.signal import ComputedSignal, Effect, Signal, batch
from hiccl.transport.protocol import NullTransport, Transport
from hiccl.diff import Diff, DiffEngine


def signal(initial):
    """Create a new Signal with the given initial value."""
    return Signal(initial)


__all__ = [
    # Signal system
    "Signal",
    "ComputedSignal",
    "Effect",
    "batch",
    "signal",
    # Hiccup DSL
    "div",
    "h1",
    "h2",
    "h3",
    "p",
    "span",
    "button",
    "input_",
    "ul",
    "ol",
    "li",
    "a",
    "form",
    "label",
    "select",
    "option",
    "textarea",
    "img",
    "br_",
    "hr_",
    "table",
    "tr",
    "td",
    "th",
    "thead",
    "tbody",
    "section",
    "header",
    "footer",
    "nav",
    "main",
    "raw",
    "fragment",
    # Component system
    "Component",
    "ActionRef",
    "BoundAction",
    "server",
    # Registry
    "ComponentRegistry",
    "set_registry",
    "component",
    # EventBus
    "EventBus",
    "event_bus",
    # Renderer
    "HiccupRenderer",
    "autobind",
    # Scheduler
    "RenderScheduler",
    # Session
    "Session",
    # Transport
    "Transport",
    "NullTransport",
    # Diff Engine
    "Diff",
    "DiffEngine",
    # App
    "HicclConfig",
    "create_hiccl_app",
    "run_dev",
    "menu",
    "hiccl_default_layout",
    "hiccl_card_layout",
    "hiccl_raw_layout",
]
