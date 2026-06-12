"""Hiccl Hiccup DSL — Full HTML5 tag functions, HiccupNode type & utilities.

Usage::

    from hiccl.hiccup import div, h1, p, span, a, img, input_

    div({"class": "container"},
        h1("Hello, world!"),
        p("This is a ", span({"class": "highlight"}, "paragraph"), "."),
        a({"href": "https://example.com"}, "Link"),
        img({"src": "photo.jpg", "alt": "A photo"}),
        input_({"type": "text", "placeholder": "Search..."}),
    )
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias


# ═══════════════════════════════════════════════════════════════════════════
# Type alias
# ═══════════════════════════════════════════════════════════════════════════

# A Hiccup node is either a string leaf or a list [tag, attrs_dict_or_None, *children]
HiccupNode: TypeAlias = str | list

# ═══════════════════════════════════════════════════════════════════════════
# Void (self-closing) elements — must not have children
# ═══════════════════════════════════════════════════════════════════════════

VOID_ELEMENTS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

# ═══════════════════════════════════════════════════════════════════════════
# Core helpers
# ═══════════════════════════════════════════════════════════════════════════


def normalize_child(child: object) -> str | list:
    """Ensure leaf nodes are unified as strings."""
    if isinstance(child, (str, list)):
        return child
    return str(child)


def tag(name: str) -> Callable[..., list]:
    """Factory: generate a tag function for the given HTML/SVG element name.

    Returns a callable that, when invoked as ``fn(*args)``, produces a
    Hiccup node of the form ``[name, attrs_dict_or_None, *children]``.

    If the first positional argument is a ``dict`` it is treated as the
    attributes map; otherwise ``None`` is used and all arguments become
    children.

    Example::

        div({"class": "box"}, "hello")
        # → ["div", {"class": "box"}, "hello"]

        p("plain text")
        # → ["p", None, "plain text"]
    """

    def fn(*args: object) -> list:
        if args and isinstance(args[0], dict):
            return [name, args[0], *[normalize_child(c) for c in args[1:]]]
        return [name, None, *[normalize_child(c) for c in args]]

    fn.__name__ = name
    fn.__qualname__ = name
    fn.__doc__ = (
        f"Return a ``<{name}>`` Hiccup node.\n\n"
        "See :func:`hiccl.hiccup.tag` for calling conventions."
    )
    return fn


# Keep private alias for backward-compatibility
_tag = tag

# ═══════════════════════════════════════════════════════════════════════════
# HTML5 tag functions — organized by category
# ═══════════════════════════════════════════════════════════════════════════

# ── Document structure ────────────────────────────────────────────────────
html = tag("html")
head = tag("head")
body = tag("body")

# ── Document metadata ─────────────────────────────────────────────────────
title = tag("title")
meta = tag("meta")  # void element
link = tag("link")  # void element
style = tag("style")
base = tag("base")  # void element

# ── Content sectioning ────────────────────────────────────────────────────
address = tag("address")
article = tag("article")
aside = tag("aside")
footer = tag("footer")
header = tag("header")
h1 = tag("h1")
h2 = tag("h2")
h3 = tag("h3")
h4 = tag("h4")
h5 = tag("h5")
h6 = tag("h6")
hgroup = tag("hgroup")
main = tag("main")
nav = tag("nav")
section = tag("section")
search = tag("search")  # HTML Living Standard §4.4 (2023+)

# ── Text content ──────────────────────────────────────────────────────────
blockquote = tag("blockquote")
dd = tag("dd")
div = tag("div")
dl = tag("dl")
dt = tag("dt")
figcaption = tag("figcaption")
figure = tag("figure")
hr = tag("hr")  # void element
hr_ = hr  # alias for backward compatibility
li = tag("li")
ol = tag("ol")
p = tag("p")
pre = tag("pre")
ul = tag("ul")

# ── Inline text semantics ─────────────────────────────────────────────────
a = tag("a")
abbr = tag("abbr")
b = tag("b")
bdi = tag("bdi")
bdo = tag("bdo")
br = tag("br")  # void element
br_ = br  # alias for backward compatibility
cite = tag("cite")
code = tag("code")
data = tag("data")
dfn = tag("dfn")
em = tag("em")
i = tag("i")
kbd = tag("kbd")
mark = tag("mark")
q = tag("q")
rp = tag("rp")
rt = tag("rt")
ruby = tag("ruby")
s = tag("s")
samp = tag("samp")
small = tag("small")
span = tag("span")
strong = tag("strong")
sub = tag("sub")
sup = tag("sup")
time = tag("time")
u = tag("u")
var = tag("var")
wbr = tag("wbr")  # void element

# ── Image & multimedia ────────────────────────────────────────────────────
area = tag("area")  # void element
audio = tag("audio")
img = tag("img")  # void element
map_ = tag("map")  # trailing _ avoids shadowing Python built-in map()
track = tag("track")  # void element
video = tag("video")

# ── Embedded content ──────────────────────────────────────────────────────
embed = tag("embed")  # void element
iframe = tag("iframe")
object_ = tag("object")  # trailing _ avoids shadowing Python built-in object()
param = tag("param")  # void element
picture = tag("picture")
portal = tag("portal")  # experimental
source = tag("source")  # void element

# ── Scripting ─────────────────────────────────────────────────────────────
canvas = tag("canvas")
noscript = tag("noscript")
script = tag("script")

# ── Demarcating edits ─────────────────────────────────────────────────────
del_ = tag("del")  # trailing _ avoids collision with Python keyword `del`
ins = tag("ins")

# ── Table content ─────────────────────────────────────────────────────────
caption = tag("caption")
col = tag("col")  # void element
colgroup = tag("colgroup")
table = tag("table")
tbody = tag("tbody")
td = tag("td")
tfoot = tag("tfoot")
th = tag("th")
thead = tag("thead")
tr = tag("tr")

# ── Forms ─────────────────────────────────────────────────────────────────
button = tag("button")
datalist = tag("datalist")
fieldset = tag("fieldset")
form = tag("form")
input_ = tag("input")  # void element; trailing _ avoids shadowing built-in input()
label = tag("label")
legend = tag("legend")
meter = tag("meter")
optgroup = tag("optgroup")
option = tag("option")
output = tag("output")
progress = tag("progress")
select = tag("select")
select_ = select  # alias for backward compatibility / clarity
selectedoption = tag("selectedoption")  # HTML Living Standard (Customizable Select)
textarea = tag("textarea")

# ── Interactive elements ──────────────────────────────────────────────────
details = tag("details")
dialog = tag("dialog")
menu = tag("menu")
summary = tag("summary")

# ── Web components ────────────────────────────────────────────────────────
slot = tag("slot")
template = tag("template")

# ── Deprecated / legacy (still encountered in the wild) ───────────────────
# Included for completeness when rendering or transforming legacy HTML.
# Do not use in new markup.
acronym = tag("acronym")  # use <abbr> instead
big = tag("big")  # use CSS font-size instead
center = tag("center")  # use CSS text-align instead
font = tag("font")  # use CSS instead
nobr = tag("nobr")  # use CSS white-space: nowrap instead
spacer = tag("spacer")  # Netscape-era; avoided in modern HTML
strike = tag("strike")  # use <s> or <del> instead
tt = tag("tt")  # use <code> or <kbd> instead

# ═══════════════════════════════════════════════════════════════════════════
# SVG elements
# ═══════════════════════════════════════════════════════════════════════════
# Naming conventions:
#   - Elements that clash with Python keywords or builtins get a trailing _
#   - Elements that clash with HTML functions defined above get an svg_ prefix
#   - All other names are used as-is (SVG namespace is inferred by the renderer)

# ── SVG structural ────────────────────────────────────────────────────────
svg = tag("svg")
defs = tag("defs")
g = tag("g")
symbol = tag("symbol")
use = tag("use")
switch_ = tag(
    "switch"
)  # trailing _ avoids shadowing Python built-in (none, but clear intent)
foreignObject = tag("foreignObject")
metadata = tag("metadata")
svg_title = tag("title")  # alias; same element name as HTML <title>
svg_style = tag("style")  # alias; same element name as HTML <style>
svg_script = tag("script")  # alias; same element name as HTML <script>
svg_view = tag("view")

# ── SVG shapes ────────────────────────────────────────────────────────────
circle = tag("circle")
ellipse = tag("ellipse")
line = tag("line")
path = tag("path")
polygon = tag("polygon")
polyline = tag("polyline")
rect = tag("rect")

# ── SVG text ──────────────────────────────────────────────────────────────
svg_text = tag("text")  # prefix avoids shadowing Python built-in str alias
textPath = tag("textPath")
tspan = tag("tspan")

# ── SVG image ─────────────────────────────────────────────────────────────
image = tag("image")

# ── SVG paint & gradients ─────────────────────────────────────────────────
linearGradient = tag("linearGradient")
radialGradient = tag("radialGradient")
stop = tag("stop")
pattern = tag("pattern")

# ── SVG clipping, masking & compositing ───────────────────────────────────
clipPath = tag("clipPath")
mask = tag("mask")
marker = tag("marker")

# ── SVG filters ───────────────────────────────────────────────────────────
filter_ = tag("filter")  # trailing _ avoids shadowing Python built-in filter()
feBlend = tag("feBlend")
feColorMatrix = tag("feColorMatrix")
feComponentTransfer = tag("feComponentTransfer")
feComposite = tag("feComposite")
feConvolveMatrix = tag("feConvolveMatrix")
feDiffuseLighting = tag("feDiffuseLighting")
feDisplacementMap = tag("feDisplacementMap")
feDistantLight = tag("feDistantLight")
feDropShadow = tag("feDropShadow")
feFlood = tag("feFlood")
feFuncA = tag("feFuncA")
feFuncB = tag("feFuncB")
feFuncG = tag("feFuncG")
feFuncR = tag("feFuncR")
feGaussianBlur = tag("feGaussianBlur")
feImage = tag("feImage")
feMerge = tag("feMerge")
feMergeNode = tag("feMergeNode")
feMorphology = tag("feMorphology")
feOffset = tag("feOffset")
fePointLight = tag("fePointLight")
feSpecularLighting = tag("feSpecularLighting")
feSpotLight = tag("feSpotLight")
feTile = tag("feTile")
feTurbulence = tag("feTurbulence")

# ── SVG animation ─────────────────────────────────────────────────────────
animate = tag("animate")
animateMotion = tag("animateMotion")
animateTransform = tag("animateTransform")
mpath = tag("mpath")
set_ = tag("set")  # trailing _ avoids shadowing Python built-in set()

# ═══════════════════════════════════════════════════════════════════════════
# Special / utility nodes
# ═══════════════════════════════════════════════════════════════════════════


def raw(html_string: str) -> list:
    """Mark as raw HTML — the content will *not* be escaped during render.

    Example::

        raw("<script>console.log('hi')</script>")
        # → ["__raw__", None, "<script>console.log('hi')</script>"]
    """
    return ["__raw__", None, html_string]


def fragment(*children: object) -> list:
    """Create a fragment node — renders children without a wrapping container.

    Example::

        fragment(li("A"), li("B"))
        # → ["__fragment__", None, ["li", None, "A"], ["li", None, "B"]]
    """
    return ["__fragment__", None, *[normalize_child(c) for c in children]]


def comment(text: str) -> list:
    """Create an HTML comment node.

    The renderer treats ``"__comment__"`` nodes specially, emitting
    ``<!-- text -->`` without escaping the text content.

    Example::

        comment("This is a comment")
        # → ["__comment__", None, "This is a comment"]
    """
    return ["__comment__", None, text]


def doctype(version: str = "html") -> str:
    """Return a DOCTYPE declaration string.

    ``version`` is one of ``"html"`` (default, HTML5), ``"4.01"``,
    ``"4.01s"`` (strict), ``"xhtml"``, ``"xhtml1"``.

    Example::

        doctype()          # → "<!DOCTYPE html>"
        doctype("4.01s")   # → '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" ...>'
    """
    _doctypes = {
        "html": "<!DOCTYPE html>",
        "4.01": (
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
            '"http://www.w3.org/TR/html4/loose.dtd">'
        ),
        "4.01s": (
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
            '"http://www.w3.org/TR/html4/strict.dtd">'
        ),
        "xhtml": (
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        ),
        "xhtml1": (
            '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" '
            '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
        ),
    }
    return _doctypes.get(version, _doctypes["html"])


def cond(condition: object, node: object) -> list | None:
    """Return *node* when *condition* is truthy, otherwise ``None``.

    Renderers that skip ``None`` children can use this to conditionally
    include nodes without inline ``if`` expressions cluttering the tree.

    Example::

        ul(
            li("Always"),
            cond(is_admin, li("Admin panel")),
        )
    """
    if condition:
        return normalize_child(node)  # type: ignore[return-value]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Attribute helpers
# ═══════════════════════════════════════════════════════════════════════════


def classes(*args: str | None | bool) -> str:
    """Build a CSS class string from arguments, skipping falsy/None values.

    Example::

        classes("btn", "btn-primary", is_active and "active")
        # → "btn btn-primary active"
        classes("card", None, False)
        # → "card"
    """
    return " ".join(str(a) for a in args if a)


def styles(**kwargs: str | int | float | None) -> str:
    """Build an inline CSS ``style`` string from keyword arguments.

    Underscores in keys are converted to hyphens (Python-friendly naming).
    Values that are ``None`` are skipped.

    Example::

        styles(display="flex", gap="8px", background_color="#fff")
        # → "display:flex; gap:8px; background-color:#fff"
    """
    parts: list[str] = []
    for k, v in kwargs.items():
        if v is None:
            continue
        css_key = k.replace("_", "-")
        parts.append(f"{css_key}:{v}")
    return "; ".join(parts)


def aria(**kwargs: str | int | float | bool | None) -> dict[str, str]:
    """Build a dict of ``aria-*`` attributes from keyword arguments.

    Underscores in keys are converted to hyphens.
    Boolean ``True``/``False`` become the strings ``"true"``/``"false"``.
    ``None`` values are skipped.

    Example::

        aria(label="Close", expanded=True, hidden=False)
        # → {"aria-label": "Close", "aria-expanded": "true", "aria-hidden": "false"}

    Merge into an attrs dict with ``merge_attrs``::

        button(merge_attrs({"class": "btn"}, aria(label="Close")), "×")
    """
    result: dict[str, str] = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        key = "aria-" + k.replace("_", "-")
        result[key] = "true" if v is True else "false" if v is False else str(v)
    return result


def data_attrs(**kwargs: str | int | float | None) -> dict[str, str]:
    """Build a dict of ``data-*`` attributes from keyword arguments.

    Underscores in keys are converted to hyphens.
    ``None`` values are skipped.

    Example::

        data_attrs(user_id="42", role="admin")
        # → {"data-user-id": "42", "data-role": "admin"}
    """
    result: dict[str, str] = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        key = "data-" + k.replace("_", "-")
        result[key] = str(v)
    return result


def hx(**kwargs: str | int | float | None) -> dict[str, str]:
    """Build a dict of ``hx-*`` (htmx) attributes from keyword arguments.

    Underscores in keys are converted to hyphens.
    ``None`` values are skipped.

    Example::

        hx(get="/items", target="#list", swap="outerHTML")
        # → {"hx-get": "/items", "hx-target": "#list", "hx-swap": "outerHTML"}
    """
    result: dict[str, str] = {}
    for k, v in kwargs.items():
        if v is None:
            continue
        key = "hx-" + k.replace("_", "-")
        result[key] = str(v)
    return result


def merge_attrs(*dicts: dict | None) -> dict:
    """Shallow-merge multiple attribute dicts, skipping ``None`` entries.

    Later dicts override earlier ones for the same key, *except* for
    ``"class"`` which is concatenated with a space separator.

    Example::

        merge_attrs({"class": "btn"}, aria(label="Close"), {"class": "active"})
        # → {"class": "btn active", "aria-label": "Close"}
    """
    result: dict = {}
    for d in dicts:
        if not d:
            continue
        for k, v in d.items():
            if k == "class" and "class" in result:
                result["class"] = f"{result['class']} {v}"
            else:
                result[k] = v
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Module exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    # ── Type ──────────────────────────────────────────────────────────────
    "HiccupNode",
    # ── Constants ─────────────────────────────────────────────────────────
    "VOID_ELEMENTS",
    # ── Core ──────────────────────────────────────────────────────────────
    "tag",
    "normalize_child",
    # ── Document structure ────────────────────────────────────────────────
    "html",
    "head",
    "body",
    # ── Document metadata ─────────────────────────────────────────────────
    "title",
    "meta",
    "link",
    "style",
    "base",
    # ── Content sectioning ────────────────────────────────────────────────
    "address",
    "article",
    "aside",
    "footer",
    "header",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hgroup",
    "main",
    "nav",
    "section",
    "search",
    # ── Text content ──────────────────────────────────────────────────────
    "blockquote",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "hr",
    "hr_",
    "li",
    "ol",
    "p",
    "pre",
    "ul",
    # ── Inline text semantics ─────────────────────────────────────────────
    "a",
    "abbr",
    "b",
    "bdi",
    "bdo",
    "br",
    "br_",
    "cite",
    "code",
    "data",
    "dfn",
    "em",
    "i",
    "kbd",
    "mark",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
    "wbr",
    # ── Image & multimedia ────────────────────────────────────────────────
    "area",
    "audio",
    "img",
    "map_",
    "track",
    "video",
    # ── Embedded content ──────────────────────────────────────────────────
    "embed",
    "iframe",
    "object_",
    "param",
    "picture",
    "portal",
    "source",
    # ── Scripting ─────────────────────────────────────────────────────────
    "canvas",
    "noscript",
    "script",
    # ── Demarcating edits ─────────────────────────────────────────────────
    "del_",
    "ins",
    # ── Table content ─────────────────────────────────────────────────────
    "caption",
    "col",
    "colgroup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    # ── Forms ─────────────────────────────────────────────────────────────
    "button",
    "datalist",
    "fieldset",
    "form",
    "input_",
    "label",
    "legend",
    "meter",
    "optgroup",
    "option",
    "output",
    "progress",
    "select",
    "select_",
    "selectedoption",
    "textarea",
    # ── Interactive elements ──────────────────────────────────────────────
    "details",
    "dialog",
    "menu",
    "summary",
    # ── Web components ────────────────────────────────────────────────────
    "slot",
    "template",
    # ── Deprecated / legacy ───────────────────────────────────────────────
    "acronym",
    "big",
    "center",
    "font",
    "nobr",
    "spacer",
    "strike",
    "tt",
    # ── SVG structural ────────────────────────────────────────────────────
    "svg",
    "defs",
    "g",
    "symbol",
    "use",
    "switch_",
    "foreignObject",
    "metadata",
    "svg_title",
    "svg_style",
    "svg_script",
    "svg_view",
    # ── SVG shapes ────────────────────────────────────────────────────────
    "circle",
    "ellipse",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    # ── SVG text ──────────────────────────────────────────────────────────
    "svg_text",
    "textPath",
    "tspan",
    # ── SVG image ─────────────────────────────────────────────────────────
    "image",
    # ── SVG paint & gradients ─────────────────────────────────────────────
    "linearGradient",
    "radialGradient",
    "stop",
    "pattern",
    # ── SVG clipping, masking & compositing ───────────────────────────────
    "clipPath",
    "mask",
    "marker",
    # ── SVG filters ───────────────────────────────────────────────────────
    "filter_",
    "feBlend",
    "feColorMatrix",
    "feComponentTransfer",
    "feComposite",
    "feConvolveMatrix",
    "feDiffuseLighting",
    "feDisplacementMap",
    "feDistantLight",
    "feDropShadow",
    "feFlood",
    "feFuncA",
    "feFuncB",
    "feFuncG",
    "feFuncR",
    "feGaussianBlur",
    "feImage",
    "feMerge",
    "feMergeNode",
    "feMorphology",
    "feOffset",
    "fePointLight",
    "feSpecularLighting",
    "feSpotLight",
    "feTile",
    "feTurbulence",
    # ── SVG animation ─────────────────────────────────────────────────────
    "animate",
    "animateMotion",
    "animateTransform",
    "mpath",
    "set_",
    # ── Special nodes ─────────────────────────────────────────────────────
    "raw",
    "fragment",
    "comment",
    "doctype",
    "cond",
    # ── Attribute helpers ─────────────────────────────────────────────────
    "classes",
    "styles",
    "aria",
    "data_attrs",
    "hx",
    "merge_attrs",
]
