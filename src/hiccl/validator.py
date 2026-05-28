"""Hiccl FormValidator — reactive Signal-driven form validation toolkit."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from hiccl.signal import ComputedSignal, Signal


class FormValidator:
    """Reactive, Signal-driven Form Validation utility for Hiccl."""

    def __init__(self, rules: dict[str, list[Callable[[Any], str | None]]]) -> None:
        self.rules = rules
        self.errors = Signal[dict[str, str]]({})
        self.is_valid = ComputedSignal(lambda: len(self.errors.get()) == 0)

    def validate(self, data: dict[str, Any]) -> bool:
        """Validate input data. Updates errors Signal. Returns True if valid."""
        new_errors: dict[str, str] = {}
        for field, field_rules in self.rules.items():
            val = data.get(field)
            for rule in field_rules:
                err_msg = rule(val)
                if err_msg:
                    new_errors[field] = err_msg
                    break  # Stop checking rules on first error
        self.errors.set(new_errors)
        return len(new_errors) == 0

    def get_error(self, field: str) -> str:
        """Reactive getter for error message of a field."""
        return self.errors.get().get(field, "")


# ---------------------------------------------------------------------------
# Out-of-the-box validation rule factories
# ---------------------------------------------------------------------------


def required(message: str = "This field is required.") -> Callable[[Any], str | None]:
    def rule(val: Any) -> str | None:
        if val is None:
            return message
        if isinstance(val, str) and not val.strip():
            return message
        return None
    return rule


def min_length(limit: int, message: str | None = None) -> Callable[[Any], str | None]:
    default_msg = f"Must be at least {limit} characters."
    msg = message or default_msg

    def rule(val: Any) -> str | None:
        if val is None:
            return None
        if len(str(val)) < limit:
            return msg
        return None
    return rule


def email(message: str = "Invalid email address.") -> Callable[[Any], str | None]:
    pattern = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

    def rule(val: Any) -> str | None:
        if not val:
            return None
        if not pattern.match(str(val)):
            return message
        return None
    return rule
