import os
import tempfile
import unittest

from sps_pyb.flash.lib.app.storage import (
    HISTORY_HEADER,
    StorageManager,
    format_history_row,
    history_path_for_timestamp,
)


def _record(timestamp_utc, pm_1_0=1.0):
    return {
        "timestamp_utc": timestamp_utc,
        "pm_1_0": pm_1_0,
        "pm_2_5": 2.0,
        "pm_4_0": 3.0,
        "pm_10_0": 4.0,
        "temp": 25.0,
        "humidity": 60.0,
    }


class StorageTests(unittest.TestCase):
    def test_format_history_row_uses_expected_column_order(self):
        row = format_history_row(_record("2026-04-17T00:00:00Z"))
        self.assertEqual(row, "2026-04-17T00:00:00Z,1.0,2.0,3.0,4.0,25.0,60.0")

    def test_append_history_writes_single_header(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "sd")
            os.mkdir(root)
            store = StorageManager(root=root, history_enabled=True)

            store.append_history(_record("2026-04-17T00:00:00Z"))
            store.append_history(_record("2026-04-17T00:01:00Z", pm_1_0=1.5))

            path = history_path_for_timestamp(root, "2026-04-17T00:00:00Z")
            with open(path, "r") as handle:
                lines = handle.read().splitlines()

            self.assertEqual(lines[0], HISTORY_HEADER)
            self.assertEqual(lines[1], "2026-04-17T00:00:00Z,1.0,2.0,3.0,4.0,25.0,60.0")
            self.assertEqual(lines[2], "2026-04-17T00:01:00Z,1.5,2.0,3.0,4.0,25.0,60.0")

    def test_queue_checkpoint_and_compaction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "sd")
            os.mkdir(root)
            store = StorageManager(root=root, history_enabled=True)

            first = _record("2026-04-17T00:00:00Z")
            second = _record("2026-04-17T00:01:00Z", pm_1_0=1.5)

            store.append_queue(first)
            store.append_queue(second)

            pending = list(store.iter_pending())
            self.assertEqual(len(pending), 2)
            self.assertEqual(pending[0][2]["timestamp_utc"], first["timestamp_utc"])
            self.assertEqual(pending[1][2]["timestamp_utc"], second["timestamp_utc"])

            store.mark_queue_offset(pending[0][1])
            store.compact_queue()

            self.assertEqual(store.load_queue_offset(), 0)
            remaining = list(store.iter_pending())
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0][2]["timestamp_utc"], second["timestamp_utc"])

            store.mark_queue_offset(remaining[0][1])
            store.compact_queue()
            self.assertFalse(os.path.exists(store.queue_path))


if __name__ == "__main__":
    unittest.main()
