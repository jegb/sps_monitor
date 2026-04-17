import json
from pathlib import Path

from .payload import PAYLOAD_FIELDS, dumps_json

HISTORY_FIELDS = ("timestamp_utc",) + PAYLOAD_FIELDS
HISTORY_HEADER = ",".join(HISTORY_FIELDS)


def history_path_for_timestamp(root, timestamp_utc):
    return Path(root) / "history" / ("%s.csv" % timestamp_utc[:10])


def format_history_row(record):
    return ",".join("" if record.get(field) is None else str(record.get(field)) for field in HISTORY_FIELDS)


class StorageManager:
    def __init__(self, root, history_enabled=True):
        self.root = Path(root)
        self.history_enabled = history_enabled
        self.history_dir = self.root / "history"
        self.queue_dir = self.root / "queue"
        self.queue_path = self.queue_dir / "pending.jsonl"
        self.state_path = self.queue_dir / "state.json"

    def has_durable_storage(self):
        return self.root.exists()

    def prepare(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        if self.history_enabled:
            self.history_dir.mkdir(parents=True, exist_ok=True)
        return True

    def append_history(self, record):
        if not self.history_enabled:
            return False

        self.prepare()
        path = history_path_for_timestamp(self.root, record["timestamp_utc"])
        write_header = (not path.exists()) or path.stat().st_size == 0

        with path.open("a", encoding="utf-8") as handle:
            if write_header:
                handle.write(HISTORY_HEADER + "\n")
            handle.write(format_history_row(record) + "\n")

        return True

    def append_queue(self, record):
        self.prepare()
        with self.queue_path.open("ab") as handle:
            handle.write(dumps_json(record).encode("utf-8"))
            handle.write(b"\n")
        return True

    def load_queue_offset(self):
        if not self.state_path.exists():
            return 0
        return int(json.loads(self.state_path.read_text(encoding="utf-8")).get("offset", 0))

    def mark_queue_offset(self, offset):
        self.prepare()
        self.state_path.write_text(dumps_json({"offset": int(offset)}), encoding="utf-8")
        return True

    def iter_pending(self, limit=None):
        if not self.queue_path.exists():
            return

        count = 0
        with self.queue_path.open("rb") as handle:
            handle.seek(self.load_queue_offset())
            while True:
                record_offset = handle.tell()
                line = handle.readline()
                if not line:
                    break

                next_offset = handle.tell()
                if not line.strip():
                    continue

                yield record_offset, next_offset, json.loads(line.decode("utf-8"))

                count += 1
                if limit is not None and count >= limit:
                    break

    def compact_queue(self):
        if not self.queue_path.exists():
            self.mark_queue_offset(0)
            return False

        offset = self.load_queue_offset()
        if offset <= 0:
            return False

        with self.queue_path.open("rb") as source:
            source.seek(offset)
            remaining = source.read()

        if remaining:
            tmp_path = self.queue_path.with_suffix(".tmp")
            tmp_path.write_bytes(remaining)
            tmp_path.replace(self.queue_path)
        else:
            self.queue_path.unlink(missing_ok=True)

        self.mark_queue_offset(0)
        return True
