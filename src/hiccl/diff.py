"""Hiccl DiffEngine — Keyed collection diffing using Longest Increasing Subsequence (LIS)."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class Diff(Generic[T]):
    """Represents the difference between two collections.

    Attributes:
        added:    Items added, represented as tuples of (new_position, item).
        removed:  Items removed from the collection.
        moved:    Moved items, mapping old_position -> new_position.
        updated:  Updated items, represented as tuples of (new_position, new_item).
    """

    added: list[tuple[int, T]] = field(default_factory=list)
    removed: list[T] = field(default_factory=list)
    moved: dict[int, int] = field(default_factory=dict)
    updated: list[tuple[int, T]] = field(default_factory=list)


def get_lis_indices(seq: list[int]) -> list[int]:
    """Calculate the indices of the Longest Increasing Subsequence of seq in O(N log N)."""
    if not seq:
        return []

    # tails[i] stores the index in seq of the smallest tail of all increasing subsequences of length i+1 found so far
    # parents[i] stores the index of the predecessor of seq[i] in the LIS ending at seq[i]
    tails = [0]
    parents = [-1] * len(seq)

    for i in range(1, len(seq)):
        if seq[i] > seq[tails[-1]]:
            parents[i] = tails[-1]
            tails.append(i)
        else:
            # Binary search to find the replacement position
            low, high = 0, len(tails) - 1
            while low < high:
                mid = (low + high) // 2
                if seq[tails[mid]] < seq[i]:
                    low = mid + 1
                else:
                    high = mid
            if seq[i] < seq[tails[low]]:
                if low > 0:
                    parents[i] = tails[low - 1]
                tails[low] = i

    # Reconstruct LIS indices from parents
    lis_indices = []
    curr = tails[-1]
    while curr != -1:
        lis_indices.append(curr)
        curr = parents[curr]
    lis_indices.reverse()
    return lis_indices


class DiffEngine:
    """Computes and applies the minimum operations to reconcile two collections of keyed items."""

    @staticmethod
    def diff_by(old: list[T], new: list[T], key_fn: Callable[[T], Any]) -> Diff[T]:
        """Compute the difference between old and new lists based on unique keys."""
        old_keys = {key_fn(item): idx for idx, item in enumerate(old)}
        new_keys = {key_fn(item): idx for idx, item in enumerate(new)}

        added = []
        removed = []
        updated = []
        moved = {}

        # 1. Identify removed items
        for item in old:
            key = key_fn(item)
            if key not in new_keys:
                removed.append(item)

        # 2. Identify added items
        for idx, item in enumerate(new):
            key = key_fn(item)
            if key not in old_keys:
                added.append((idx, item))

        # 3. Identify matches, updates, and sequence for LIS
        matching_new_indices = []
        matching_old_indices = []
        for idx, item in enumerate(new):
            key = key_fn(item)
            if key in old_keys:
                old_idx = old_keys[key]
                matching_new_indices.append(idx)
                matching_old_indices.append(old_idx)
                # Check for changes in the item value
                if old[old_idx] != item:
                    updated.append((idx, item))

        # 4. Find LIS of matching old indices to minimize moves
        lis_seq_indices = get_lis_indices(matching_old_indices)
        lis_new_indices = {matching_new_indices[i] for i in lis_seq_indices}

        for i, new_idx in enumerate(matching_new_indices):
            if new_idx not in lis_new_indices:
                old_idx = matching_old_indices[i]
                moved[old_idx] = new_idx

        return Diff(added=added, removed=removed, moved=moved, updated=updated)

    @staticmethod
    def apply_diff(base: list[T], diff: Diff[T], key_fn: Callable[[T], Any]) -> list[T]:
        """Apply the computed Diff to base list and reconstruct the new list."""
        removed_keys = {key_fn(item) for item in diff.removed}
        remaining = [item for item in base if key_fn(item) not in removed_keys]

        # Apply updates
        updated_map = {key_fn(item): item for _, item in diff.updated}
        for i, item in enumerate(remaining):
            key = key_fn(item)
            if key in updated_map:
                remaining[i] = updated_map[key]

        total_len = len(remaining) + len(diff.added)
        new_list: list[T | None] = [None] * total_len

        # Place added items at their specified positions
        for pos, item in diff.added:
            new_list[pos] = item

        # Place moved items at their specified positions
        moved_keys = set()
        for old_pos, new_pos in diff.moved.items():
            item = base[old_pos]
            key = key_fn(item)
            if key in updated_map:
                item = updated_map[key]
            new_list[new_pos] = item
            moved_keys.add(key)

        # Place the remaining non-moved, non-added items in the vacant spots in relative order
        remaining_idx = 0
        for i in range(total_len):
            if new_list[i] is None:
                while (
                    remaining_idx < len(remaining)
                    and key_fn(remaining[remaining_idx]) in moved_keys
                ):
                    remaining_idx += 1
                if remaining_idx < len(remaining):
                    new_list[i] = remaining[remaining_idx]
                    remaining_idx += 1

        return new_list  # type: ignore[return-value]
