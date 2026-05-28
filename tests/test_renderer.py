"""Tests for hiccl.renderer — HiccupRenderer HTML serialization."""

from hiccl.component import Component
from hiccl.hiccup import fragment, raw
from hiccl.renderer import HiccupRenderer
from hiccl.signal import Signal


class TestHiccupRendererRender:
    def setup_method(self):
        self.r = HiccupRenderer()

    def test_string_escaped(self):
        assert self.r.render("hello <world>") == "hello &lt;world&gt;"

    def test_simple_tag(self):
        result = self.r.render(["div", None, "hello"])
        assert result == "<div>hello</div>"

    def test_tag_with_attrs(self):
        result = self.r.render(["div", {"class": "box", "id": "main"}, "hi"])
        assert result == '<div class="box" id="main">hi</div>'

    def test_nested_tags(self):
        result = self.r.render(["div", None, ["p", None, "inner"]])
        assert result == "<div><p>inner</p></div>"

    def test_void_element(self):
        result = self.r.render(["br", None])
        assert result == "<br>"

    def test_input_void(self):
        result = self.r.render(["input", {"type": "text"}])
        assert result == '<input type="text">'

    def test_img_void(self):
        result = self.r.render(["img", {"src": "pic.jpg"}])
        assert result == '<img src="pic.jpg">'

    def test_boolean_attr_true(self):
        result = self.r.render(["input", {"disabled": True}])
        assert result == "<input disabled>"

    def test_boolean_attr_false(self):
        result = self.r.render(["input", {"disabled": False}])
        assert result == "<input>"

    def test_none_attr_skipped(self):
        result = self.r.render(["div", {"data-x": None}])
        assert result == "<div></div>"

    def test_list_attr(self):
        result = self.r.render(["div", {"class": ["a", "b", "c"]}])
        assert result == '<div class="a b c"></div>'

    def test_attr_escaping(self):
        result = self.r.render(["div", {"title": 'say "hello"'}, "x"])
        assert result == '<div title="say &quot;hello&quot;">x</div>'

    def test_raw_html(self):
        result = self.r.render(raw("<b>bold</b>"))
        assert result == "<b>bold</b>"

    def test_fragment(self):
        result = self.r.render(fragment("a", "b"))
        assert result == "ab"

    def test_empty_children(self):
        result = self.r.render(["div", None])
        assert result == "<div></div>"

    def test_multiple_children(self):
        result = self.r.render(["ul", None, ["li", None, "a"], ["li", None, "b"]])
        assert result == "<ul><li>a</li><li>b</li></ul>"

    def test_number_child(self):
        result = self.r.render(["span", None, 42])
        assert result == "<span>42</span>"

    def test_text_escaping_ampersand(self):
        result = self.r.render("a & b")
        assert result == "a &amp; b"


class TestHiccupRendererComponent:
    def test_render_component(self):
        class TestComp(Component):
            def __init__(self):
                super().__init__()
                self.component_id = "test-1"

            def render(self):
                return ["div", None, "hello"]

        r = HiccupRenderer()
        comp = TestComp()
        result = r.render_component(comp)
        assert result == '<div id="test-1">hello</div>'

    def test_render_component_cached_first(self):
        class TestComp(Component):
            def __init__(self):
                super().__init__()
                self.count = Signal(0)
                self.component_id = "cached-1"

            def render(self):
                return ["span", None, str(self.count.get())]

        r = HiccupRenderer()
        comp = TestComp()
        comp._discovered_signals()
        result = r.render_component_cached(comp)
        assert result is not None
        assert "0" in result

    def test_render_component_cached_no_change(self):
        class TestComp(Component):
            def __init__(self):
                super().__init__()
                self.count = Signal(0)
                self.component_id = "cached-2"

            def render(self):
                return ["span", None, str(self.count.get())]

        r = HiccupRenderer()
        comp = TestComp()
        comp._discovered_signals()
        r.render_component_cached(comp)  # First render
        result = r.render_component_cached(comp)  # No change
        assert result is None

    def test_render_component_cached_after_change(self):
        class TestComp(Component):
            def __init__(self):
                super().__init__()
                self.count = Signal(0)
                self.component_id = "cached-3"

            def render(self):
                return ["span", None, str(self.count.get())]

        r = HiccupRenderer()
        comp = TestComp()
        comp._discovered_signals()
        r.render_component_cached(comp)  # First render
        comp.count.set(5)
        result = r.render_component_cached(comp)
        assert result is not None
        assert "5" in result
