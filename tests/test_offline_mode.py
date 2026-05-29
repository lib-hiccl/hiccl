"""Tests for hiccl.app offline_mode font rendering."""

from hiccl.app import HicclConfig, hiccl_default_layout, hiccl_card_layout
from hiccl.registry import ComponentRegistry


class DummyRequest:
    def __init__(self):
        self.state = type("State", (), {"hiccl_session_id": "test_session_id"})()
        self.cookies = {}


def test_offline_mode_default_layout():
    registry = ComponentRegistry()

    # Online mode (default)
    config_online = HicclConfig(component_registry=registry, offline_mode=False)
    req = DummyRequest()
    html_online = hiccl_default_layout(
        req, "<div>Comp</div>", "<ul>Menu</ul>", config_online
    )
    assert "fonts.googleapis.com" in html_online
    assert "Plus Jakarta Sans" in html_online

    # Offline mode
    config_offline = HicclConfig(component_registry=registry, offline_mode=True)
    html_offline = hiccl_default_layout(
        req, "<div>Comp</div>", "<ul>Menu</ul>", config_offline
    )
    assert "fonts.googleapis.com" not in html_offline
    assert "system-ui" in html_offline


def test_offline_mode_card_layout():
    registry = ComponentRegistry()

    # Online mode (default)
    config_online = HicclConfig(component_registry=registry, offline_mode=False)
    req = DummyRequest()
    html_online = hiccl_card_layout(
        req, "<div>Comp</div>", "<ul>Menu</ul>", config_online
    )
    assert "fonts.googleapis.com" in html_online
    assert "Plus Jakarta Sans" in html_online

    # Offline mode
    config_offline = HicclConfig(component_registry=registry, offline_mode=True)
    html_offline = hiccl_card_layout(
        req, "<div>Comp</div>", "<ul>Menu</ul>", config_offline
    )
    assert "fonts.googleapis.com" not in html_offline
    assert "system-ui" in html_offline
