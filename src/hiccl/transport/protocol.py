"""Hiccl protocol — message models and transport protocol definitions."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Wire protocol messages (JSON between server and client)
# ---------------------------------------------------------------------------


class PatchMessage(BaseModel):
    """A patch to apply to a component's DOM."""

    type: str = "patch"
    component_id: str
    html: str
    swap: str = "outerHTML"
    oob: list["PatchMessage"] | None = None


class ActionMessage(BaseModel):
    """An action request from the client."""

    type: str = "action"
    component_id: str
    method: str
    args: dict = {}


class ErrorMessage(BaseModel):
    """An error message from the server."""

    type: str = "error"
    component_id: str
    message: str
    status: int = 500


class BatchMessage(BaseModel):
    """A batch of patch messages."""

    type: str = "batch"
    patches: list[PatchMessage]


# ---------------------------------------------------------------------------
# Transport protocol — abstract interface for push channels
# ---------------------------------------------------------------------------


@runtime_checkable
class Transport(Protocol):
    """Interface that Session uses to push rendered patches to the client."""

    async def push(self, patches: list[dict[str, Any]]) -> None:
        """Send rendered patches to the client."""
        ...

    def is_connected(self) -> bool:
        """Return True if the transport is alive and can push."""
        ...


class NullTransport:
    """No-op transport — used when only HTTP request/response is available."""

    async def push(self, patches: list[dict[str, Any]]) -> None:
        pass

    def is_connected(self) -> bool:
        return False
