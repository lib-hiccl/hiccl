"""Tests for hiccl.transport.protocol — Pydantic message models."""

from hiccl.transport.protocol import (
    ActionMessage,
    BatchMessage,
    ErrorMessage,
    PatchMessage,
)


class TestPatchMessage:
    def test_defaults(self):
        msg = PatchMessage(component_id="c1", html="<div>hi</div>")
        assert msg.type == "patch"
        assert msg.swap == "outerHTML"
        assert msg.oob is None

    def test_with_oob(self):
        inner = PatchMessage(component_id="c2", html="<span>oob</span>")
        msg = PatchMessage(component_id="c1", html="<div>hi</div>", oob=[inner])
        assert len(msg.oob) == 1
        assert msg.oob[0].component_id == "c2"

    def test_json_roundtrip(self):
        msg = PatchMessage(component_id="c1", html="<p>test</p>")
        data = msg.model_dump()
        assert data["type"] == "patch"
        restored = PatchMessage(**data)
        assert restored.component_id == "c1"


class TestActionMessage:
    def test_defaults(self):
        msg = ActionMessage(component_id="c1", method="increment")
        assert msg.type == "action"
        assert msg.args == {}

    def test_with_args(self):
        msg = ActionMessage(component_id="c1", method="send", args={"text": "hi"})
        assert msg.args["text"] == "hi"


class TestErrorMessage:
    def test_defaults(self):
        msg = ErrorMessage(component_id="c1", message="oops")
        assert msg.type == "error"
        assert msg.status == 500

    def test_custom_status(self):
        msg = ErrorMessage(component_id="c1", message="not found", status=404)
        assert msg.status == 404


class TestBatchMessage:
    def test_empty_batch(self):
        msg = BatchMessage(patches=[])
        assert msg.type == "batch"
        assert len(msg.patches) == 0

    def test_batch_with_patches(self):
        p1 = PatchMessage(component_id="c1", html="<div>1</div>")
        p2 = PatchMessage(component_id="c2", html="<div>2</div>")
        msg = BatchMessage(patches=[p1, p2])
        assert len(msg.patches) == 2
