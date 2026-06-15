"""Hiccl Transducers — Hiccup tree intermediate transformation middleware."""

from abc import ABC, abstractmethod
from typing import Any


class Transducer(ABC):
    """Abstract base class for all Hiccup node transducers.

    Transducers intercept, inspect, and transform DOM nodes in the Hiccup tree
    before they are compiled into HTML.

    All transformations must be pure and immutable (returning new nodes rather
    than modifying inputs in-place).
    """

    @abstractmethod
    def transform(self, node: Any) -> Any:
        """Transform a Hiccup node or leaf and return the new transformed node.

        Must return a new list/dict to preserve tree immutability.
        """
        pass


def walk_tree(node: Any, transducer: Transducer) -> Any:
    """Recursively traverse a Hiccup tree (bottom-up) and apply a transducer to every node."""
    if isinstance(node, str):
        return transducer.transform(node)

    if not isinstance(node, list) or len(node) == 0:
        return transducer.transform(node)

    tag = node[0]

    # Raw HTML: do not traverse children, just pass to transducer
    if tag == "__raw__":
        return transducer.transform(node)

    # Fragment: traverse children
    if tag == "__fragment__":
        children = node[2:] if len(node) > 2 else []
        new_children = [walk_tree(c, transducer) for c in children]
        rebuilt = [tag, node[1]] + new_children
        return transducer.transform(rebuilt)

    # Normal element: [tag, attrs?, *children]
    has_attrs = len(node) > 1 and (isinstance(node[1], dict) or node[1] is None)
    children = node[2:] if has_attrs else node[1:]

    # Walk children first (bottom-up)
    new_children = [walk_tree(c, transducer) for c in children]

    # Rebuild element node
    rebuilt = [tag]
    if has_attrs:
        # Keep original attrs dict or None. The transducer can copy it if modifying.
        rebuilt.append(node[1])
    rebuilt.extend(new_children)

    # Transform the rebuilt node
    return transducer.transform(rebuilt)


class LoadingTransducer(Transducer):
    """Automatically append a loading class and indicator to interactive buttons."""

    def __init__(self, loading_class: str = "btn-loading-indicator") -> None:
        self.loading_class = loading_class

    def transform(self, node: Any) -> Any:
        if isinstance(node, list) and len(node) > 0 and node[0] == "button":
            has_attrs = len(node) > 1 and isinstance(node[1], dict)
            attrs = node[1] if has_attrs else {}

            is_interactive = any(
                k.startswith("hx-") or k.startswith("on_") for k in attrs.keys()
            )
            if is_interactive:
                new_attrs = {**attrs}
                classes = new_attrs.get("class", "")
                if self.loading_class not in classes:
                    new_attrs["class"] = f"{classes} {self.loading_class}".strip()
                if "hx-indicator" not in new_attrs:
                    new_attrs["hx-indicator"] = "#global-spinner"

                children = node[2:] if has_attrs else node[1:]
                return [node[0], new_attrs] + children

        return node


class SanitizingTransducer(Transducer):
    """Sanitize blacklisted words in string/text leaf nodes in-place."""

    def __init__(self, blacklist: list[str], replacement: str = "***") -> None:
        self.blacklist = blacklist
        self.replacement = replacement

    def transform(self, node: Any) -> Any:
        if isinstance(node, str):
            sanitized = node
            for word in self.blacklist:
                sanitized = sanitized.replace(word, self.replacement)
            return sanitized
        return node
