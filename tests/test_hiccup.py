"""Tests for hiccl.hiccup — tag functions, raw, fragment."""

from hiccl.hiccup import (
    a,
    br_,
    button,
    div,
    form,
    fragment,
    h1,
    h2,
    hr_,
    img,
    input_,
    li,
    normalize_child,
    p,
    raw,
    span,
    table,
    td,
    th,
    tr,
    ul,
)


class TestTagFunction:
    def test_tag_no_attrs(self):
        assert div("hello") == ["div", None, "hello"]

    def test_tag_with_attrs(self):
        result = div({"class": "container"}, "hello")
        assert result == ["div", {"class": "container"}, "hello"]

    def test_tag_with_multiple_children(self):
        result = ul(li("a"), li("b"))
        assert result == ["ul", None, ["li", None, "a"], ["li", None, "b"]]

    def test_nested_tags(self):
        result = div({"id": "app"}, h1("Title"), p("content"))
        assert result == [
            "div",
            {"id": "app"},
            ["h1", None, "Title"],
            ["p", None, "content"],
        ]

    def test_empty_tag(self):
        assert div() == ["div", None]

    def test_tag_with_none_attrs(self):
        assert p("text") == ["p", None, "text"]

    def test_input_tag(self):
        result = input_({"type": "text", "name": "q"})
        assert result == ["input", {"type": "text", "name": "q"}]

    def test_br_tag(self):
        assert br_() == ["br", None]

    def test_integer_converted_to_string(self):
        result = p(42)
        assert result == ["p", None, "42"]


class TestNormalizeChild:
    def test_string_passthrough(self):
        assert normalize_child("hello") == "hello"

    def test_list_passthrough(self):
        node = ["div", None, "x"]
        assert normalize_child(node) is node

    def test_int_to_string(self):
        assert normalize_child(42) == "42"

    def test_float_to_string(self):
        assert normalize_child(3.14) == "3.14"

    def test_none_to_string(self):
        assert normalize_child(None) == "None"


class TestRaw:
    def test_raw_html(self):
        result = raw("<b>bold</b>")
        assert result == ["__raw__", None, "<b>bold</b>"]


class TestFragment:
    def test_fragment_children(self):
        result = fragment("a", "b", "c")
        assert result == ["__fragment__", None, "a", "b", "c"]

    def test_fragment_with_nested_tags(self):
        result = fragment(p("a"), p("b"))
        assert result == [
            "__fragment__",
            None,
            ["p", None, "a"],
            ["p", None, "b"],
        ]

    def test_empty_fragment(self):
        result = fragment()
        assert result == ["__fragment__", None]


class TestAllTags:
    """Ensure all tag functions are callable and produce correct structure."""

    def test_all_tags_produce_list(self):
        tags = [
            div,
            h1,
            h2,
            p,
            span,
            button,
            input_,
            ul,
            li,
            a,
            form,
            img,
            br_,
            hr_,
            table,
            tr,
            td,
            th,
        ]
        for tag_fn in tags:
            result = tag_fn()
            assert isinstance(result, list), f"{tag_fn.__name__} should return list"
            assert result[0] == tag_fn.__name__, (
                f"Tag name mismatch for {tag_fn.__name__}"
            )
