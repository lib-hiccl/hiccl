"""Hiccl Hiccup DSL — HTML tag functions + HiccupNode type."""

from __future__ import annotations

from collections.abc import Callable

# Type alias: a Hiccup node is either a string leaf or a list
# [tag, attrs_dict_or_None, *children]
type HiccupNode = str | list  # type: ignore[valid-type]


def normalize_child(child: object) -> str | list:
    """Ensure leaf nodes are unified as strings."""
    if isinstance(child, (str, list)):
        return child
    return str(child)


def _tag(name: str) -> Callable[..., list]:
    """Factory: generate a tag function for the given HTML element name."""

    def tag(*args) -> list:
        if args and isinstance(args[0], dict):
            return [name, args[0], *[normalize_child(c) for c in args[1:]]]
        return [name, None, *[normalize_child(c) for c in args]]

    tag.__name__ = name
    tag.__qualname__ = name
    return tag


# HTML5 tag functions
div = _tag("div")
h1 = _tag("h1")
h2 = _tag("h2")
h3 = _tag("h3")
p = _tag("p")
span = _tag("span")
button = _tag("button")
input_ = _tag("input")
ul = _tag("ul")
ol = _tag("ol")
li = _tag("li")
a = _tag("a")
form = _tag("form")
label = _tag("label")
select = _tag("select")
option = _tag("option")
textarea = _tag("textarea")
img = _tag("img")
br_ = _tag("br")
hr_ = _tag("hr")
table = _tag("table")
tr = _tag("tr")
td = _tag("td")
th = _tag("th")
thead = _tag("thead")
tbody = _tag("tbody")
section = _tag("section")
header = _tag("header")
footer = _tag("footer")
nav = _tag("nav")
main = _tag("main")


def raw(html_string: str) -> list:
    """Mark as raw HTML — no escaping during render."""
    return ["__raw__", None, html_string]


def fragment(*children: object) -> list:
    """Fragment — no wrapping container."""
    return ["__fragment__", None, *[normalize_child(c) for c in children]]
