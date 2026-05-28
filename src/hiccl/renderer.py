"""Hiccl HiccupRenderer — Hiccup tree → HTML serialization with autobind."""

from __future__ import annotations

import html as html_module
import json

from hiccl.component import ActionRef, Component, _in_render

# Void elements (self-closing, no children)
_VOID_ELEMENTS = frozenset(
    {
        "br",
        "hr",
        "input",
        "img",
        "meta",
        "link",
        "area",
        "base",
        "col",
        "embed",
        "source",
        "track",
        "wbr",
    }
)

# ---------------------------------------------------------------------------
# on_* event → htmx attribute mapping
# ---------------------------------------------------------------------------
# (http_method, trigger_name)
# trigger_name of None means use htmx default (click / submit)
_ON_EVENT_MAP: dict[str, tuple[str, str | None]] = {
    "on_click": ("post", None),
    "on_submit": ("post", None),
    "on_change": ("post", "change"),
    "on_input": ("post", "input"),
    "on_load": ("get", "load"),
}


# ---------------------------------------------------------------------------
# autobind — walk Hiccup tree, convert on_* ActionRefs → htmx attributes
# ---------------------------------------------------------------------------


def autobind(node: str | list, component: Component) -> str | list:
    """Walk a Hiccup tree and convert ``on_*`` ActionRefs to htmx attributes.

    Also handles the case where an ``hx-*`` attribute value is an ActionRef
    (e.g. ``{"hx-post": self.tick, "hx-trigger": "every 1s"}``).
    """
    if isinstance(node, str):
        return node

    if not isinstance(node, list) or len(node) == 0:
        return node

    tag = node[0]

    # Raw HTML — no processing needed
    if tag == "__raw__":
        return node

    # Fragment — process children
    if tag == "__fragment__":
        children = node[2:] if len(node) > 2 else []
        new_children = [autobind(c, component) for c in children]
        return [tag, node[1]] + new_children

    # Parse normal node: [tag, attrs?, *children]
    has_attrs = len(node) > 1 and isinstance(node[1], dict)
    raw_attrs = node[1] if has_attrs else None
    children = node[2:] if has_attrs else node[1:]

    # Process attributes
    attrs = dict(raw_attrs) if raw_attrs else None
    if attrs:
        _bind_events(attrs)
        _bind_hx_refs(attrs)

    # Recurse into children
    new_children = [autobind(c, component) for c in children] if children else []

    # Rebuild node
    result = [tag]
    if attrs is not None:
        result.append(attrs)
    elif has_attrs:
        result.append(raw_attrs)
    result.extend(new_children)
    return result


def _bind_events(attrs: dict) -> None:
    """Convert ``on_*`` attributes to htmx attributes in-place."""
    for on_event in list(attrs.keys()):
        if on_event not in _ON_EVENT_MAP:
            continue
        value = attrs[on_event]
        if not isinstance(value, ActionRef):
            continue

        http_method, trigger = _ON_EVENT_MAP[on_event]
        action_url = f"/hiccl/action/{value.component_id}/{value.method_name}"

        # hx-post / hx-get (only if user hasn't specified one)
        hx_attr = f"hx-{http_method}"
        if hx_attr not in attrs:
            attrs[hx_attr] = action_url

        # Auto hx-target
        if "hx-target" not in attrs:
            attrs["hx-target"] = f"#{value.component_id}"

        # Auto hx-swap
        if "hx-swap" not in attrs:
            attrs["hx-swap"] = "outerHTML"

        # Explicit trigger if not the htmx default
        if trigger is not None and "hx-trigger" not in attrs:
            attrs["hx-trigger"] = trigger

        # Pre-bound args → hx-vals
        if value.bound_args:
            attrs["hx-vals"] = json.dumps(value.bound_args)

        # Remove the on_* key
        del attrs[on_event]


def _bind_hx_refs(attrs: dict) -> None:
    """Convert ActionRef values in hx-* URL attributes to action URLs."""
    for key in list(attrs.keys()):
        if not key.startswith("hx-"):
            continue
        value = attrs[key]
        if isinstance(value, ActionRef):
            attrs[key] = f"/hiccl/action/{value.component_id}/{value.method_name}"
            # Pre-bound args go into hx-vals (merge if already present)
            if value.bound_args:
                existing = {}
                if "hx-vals" in attrs:
                    try:
                        existing = json.loads(attrs["hx-vals"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                existing.update(value.bound_args)
                attrs["hx-vals"] = json.dumps(existing)


# ---------------------------------------------------------------------------
# HiccupRenderer
# ---------------------------------------------------------------------------


class HiccupRenderer:
    """Serialize Hiccup trees to HTML strings."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[int, str]] = {}
        self._static_cache: dict[int, tuple[str | list, str]] = {}

    def _is_static_and_cache(self, node: str | list) -> tuple[bool, str]:
        """Check if a node is fully static (no ActionRefs). If so, cache and return HTML."""
        if isinstance(node, str):
            return True, html_module.escape(node, quote=False)
        if not isinstance(node, list) or len(node) == 0:
            return True, html_module.escape(str(node), quote=False)

        node_id = id(node)
        if node_id in self._static_cache:
            cached_node, cached_html = self._static_cache[node_id]
            if cached_node is node:
                return True, cached_html

        tag = node[0]
        if tag in ("__raw__", "__fragment__"):
            return False, ""

        attrs = node[1] if len(node) > 1 else None
        children = node[2:] if len(node) > 2 else []

        if attrs and isinstance(attrs, dict):
            for v in attrs.values():
                if isinstance(v, ActionRef):
                    return False, ""

        children_htmls = []
        for c in children:
            is_child_static, child_html = self._is_static_and_cache(c)
            if not is_child_static:
                return False, ""
            children_htmls.append(child_html)

        attrs_html = self._render_attrs(attrs) if attrs else ""
        children_html = "".join(children_htmls)

        if tag in _VOID_ELEMENTS:
            html_str = f"<{tag}{attrs_html}>"
        else:
            html_str = f"<{tag}{attrs_html}>{children_html}</{tag}>"

        # Safe limit to prevent unbounded memory growth
        if len(self._static_cache) < 10000:
            self._static_cache[node_id] = (node, html_str)

        return True, html_str

    def render(self, node: str | list) -> str:
        """Render a HiccupNode to an HTML string."""
        if isinstance(node, list) and len(node) > 0:
            is_static, cached_html = self._is_static_and_cache(node)
            if is_static:
                return cached_html

        if isinstance(node, str):
            return html_module.escape(node, quote=False)

        if not isinstance(node, list) or len(node) == 0:
            return html_module.escape(str(node), quote=False)

        tag = node[0]

        # Raw HTML passthrough
        if tag == "__raw__":
            return node[2] if len(node) > 2 else ""

        # Fragment — render children without wrapper
        if tag == "__fragment__":
            children = node[2:] if len(node) > 2 else []
            return "".join(self.render(c) for c in children)

        # Normal tag: [tag_name, attrs_or_None, *children]
        attrs = node[1] if len(node) > 1 else None
        children = node[2:] if len(node) > 2 else []

        attrs_html = self._render_attrs(attrs) if attrs else ""
        children_html = "".join(self.render(c) for c in children)

        if tag in _VOID_ELEMENTS:
            return f"<{tag}{attrs_html}>"

        return f"<{tag}{attrs_html}>{children_html}</{tag}>"

    def _render_attrs(self, attrs: dict) -> str:
        """Render an attribute dict to an HTML attribute string."""
        parts: list[str] = []
        for k, v in attrs.items():
            if v is True:
                parts.append(f" {k}")
            elif v is False or v is None:
                continue
            elif isinstance(v, (list, tuple)):
                joined = " ".join(str(x) for x in v)
                parts.append(f' {k}="{html_module.escape(joined, quote=True)}"')
            else:
                parts.append(f' {k}="{html_module.escape(str(v), quote=True)}"')
        return "".join(parts)

    def render_component(self, component: Component) -> str:
        """Render a component: render() → autobind → inject id → serialize."""
        # Clear the static node cache for this render cycle to prevent object id reuse issues
        self._static_cache.clear()
        # Set render context so @server methods return ActionRefs
        token = _in_render.set(True)
        try:
            hiccup = component.render()
        finally:
            _in_render.reset(token)

        # Convert on_* ActionRefs to htmx attributes
        hiccup = autobind(hiccup, component)

        # If root is a tag node, inject id into its attrs
        if (
            isinstance(hiccup, list)
            and len(hiccup) >= 1
            and isinstance(hiccup[0], str)
            and hiccup[0] not in ("__raw__", "__fragment__")
        ):
            tag = hiccup[0]
            if len(hiccup) > 1 and isinstance(hiccup[1], dict):
                # Merge id into existing attrs (copy to avoid mutation)
                merged_attrs = {**hiccup[1], "id": component.component_id}
                new_hiccup = [tag, merged_attrs] + hiccup[2:]
            else:
                # No attrs dict: insert one with just id, skip the None placeholder
                new_hiccup = [tag, {"id": component.component_id}] + hiccup[2:]
            return self.render(new_hiccup)

        # Fallback: wrap in container div
        body = self.render(hiccup)
        return f'<div id="{component.component_id}">{body}</div>'

    def render_component_cached(self, component: Component) -> str | None:
        """Cache-render: returns None if signal versions unchanged (no re-render needed)."""
        total_version = sum(s._version for s in component._signals.values())
        cached = self._cache.get(component.component_id)
        if cached and cached[0] == total_version:
            return None
        rendered = self.render_component(component)
        self._cache[component.component_id] = (total_version, rendered)
        return rendered
