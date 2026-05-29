"""hREPL Protocol — parses TCP socket stream frames."""

from __future__ import annotations

import json
from typing import Any


def parse_message(line: bytes) -> dict[str, Any]:
    """Parse JSON string from TCP socket line frame."""
    return json.loads(line.decode("utf-8").strip())


def serialize_response(status: str, **kwargs: Any) -> bytes:
    """Format standard JSON response followed by newline."""
    data = {"status": status}
    data.update(kwargs)
    return (json.dumps(data) + "\n").encode("utf-8")
