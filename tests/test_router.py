"""Tests for hiccl.router — Declarative Signal-driven Router."""

import pytest
from hiccl.component import Component
from hiccl.renderer import HiccupRenderer
from hiccl.router import Router


class HomeView(Component):
    def render(self):
        return ["div", {"class": "home"}, "Welcome Home"]


class AboutView(Component):
    def render(self):
        return ["div", {"class": "about"}, "About Us"]


def test_router_declarative_routing():
    routes = {
        "/": HomeView,
        "/about": AboutView,
        "/static-raw": lambda: ["p", None, "Static Callback HTML"]
    }

    # 1. Initialize router at "/"
    router = Router(routes, initial_path="/")
    renderer = HiccupRenderer()

    html_home = renderer.render(router.render())
    assert "Welcome Home" in html_home
    assert "About Us" not in html_home

    # 2. Navigate to "/about" programmatically
    router.navigate("/about")
    assert router.current_path.get() == "/about"

    html_about = renderer.render(router.render())
    assert "About Us" in html_about
    assert "Welcome Home" not in html_about

    # 3. Navigate to a static callback path
    router.navigate("/static-raw")
    html_static = renderer.render(router.render())
    assert "Static Callback HTML" in html_static
