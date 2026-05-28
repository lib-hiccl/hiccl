"""Tests for hiccl.diff — DiffEngine and LIS calculation."""

from hiccl.diff import DiffEngine, get_lis_indices


class TestLISIndices:
    def test_empty_seq(self):
        assert get_lis_indices([]) == []

    def test_single_element(self):
        assert get_lis_indices([5]) == [0]

    def test_increasing(self):
        assert get_lis_indices([1, 2, 3, 4, 5]) == [0, 1, 2, 3, 4]

    def test_decreasing(self):
        # LIS is just any single element, eg index of the first one
        assert len(get_lis_indices([5, 4, 3, 2, 1])) == 1

    def test_mixed(self):
        # [1, 3, 0, 2] -> LIS could be [1, 3] (values 1, 3) or [0, 2] (values 0, 2)
        indices = get_lis_indices([1, 3, 0, 2])
        assert len(indices) == 2
        # Verify it is strictly increasing
        seq = [1, 3, 0, 2]
        values = [seq[idx] for idx in indices]
        assert values == sorted(values)
        assert len(set(values)) == len(values)


class TestDiffEngine:
    def _key_fn(self, item: dict) -> str:
        return item["id"]

    def test_diff_no_changes(self):
        old = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
        new = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.moved) == 0
        assert len(diff.updated) == 0

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new

    def test_diff_added(self):
        old = [{"id": "a", "val": 1}]
        new = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        assert diff.added == [(1, {"id": "b", "val": 2})]
        assert len(diff.removed) == 0
        assert len(diff.moved) == 0
        assert len(diff.updated) == 0

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new

    def test_diff_removed(self):
        old = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
        new = [{"id": "a", "val": 1}]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        assert len(diff.added) == 0
        assert diff.removed == [{"id": "b", "val": 2}]
        assert len(diff.moved) == 0
        assert len(diff.updated) == 0

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new

    def test_diff_moved(self):
        # old: A, B, C, D
        # new: B, D, A, C
        old = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
        new = [{"id": "b"}, {"id": "d"}, {"id": "a"}, {"id": "c"}]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        # A and C are selected as LIS (0, 2), they don't move.
        # B (old pos 1 -> new pos 0) and D (old pos 3 -> new pos 1) move.
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.moved) == 2
        assert diff.moved[1] == 0  # B moved to 0
        assert diff.moved[3] == 1  # D moved to 1
        assert len(diff.updated) == 0

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new

    def test_diff_updated(self):
        old = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
        new = [{"id": "a", "val": 10}, {"id": "b", "val": 2}]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.moved) == 0
        assert diff.updated == [(0, {"id": "a", "val": 10})]

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new

    def test_complex_mixed_diff(self):
        # A, B, C, D -> B (updated), E (added), D, F (added), A
        # C is removed
        old = [
            {"id": "a", "val": 1},
            {"id": "b", "val": 2},
            {"id": "c", "val": 3},
            {"id": "d", "val": 4},
        ]
        new = [
            {"id": "b", "val": 20},  # moved and updated (pos 0)
            {"id": "e", "val": 5},  # added (pos 1)
            {"id": "d", "val": 4},  # LIS (pos 2)
            {"id": "f", "val": 6},  # added (pos 3)
            {"id": "a", "val": 1},  # moved (pos 4)
        ]

        diff = DiffEngine.diff_by(old, new, self._key_fn)
        assert diff.removed == [{"id": "c", "val": 3}]
        assert diff.added == [(1, {"id": "e", "val": 5}), (3, {"id": "f", "val": 6})]
        assert diff.updated == [(0, {"id": "b", "val": 20})]
        # B and D are selected as LIS, so A moves (old pos 0 -> new pos 4)
        assert diff.moved == {0: 4}

        # apply_diff
        reconstructed = DiffEngine.apply_diff(old, diff, self._key_fn)
        assert reconstructed == new
