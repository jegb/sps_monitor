try:
    import json
except ImportError:
    import ujson as json

try:
    import os
except ImportError:
    import uos as os

try:
    from .payload import OPTIONAL_PAYLOAD_FIELDS, PAYLOAD_FIELDS, dumps_json
except ImportError:
    from app.payload import OPTIONAL_PAYLOAD_FIELDS, PAYLOAD_FIELDS, dumps_json

HISTORY_FIELDS = ("timestamp_utc",) + PAYLOAD_FIELDS + OPTIONAL_PAYLOAD_FIELDS
HISTORY_HEADER = ",".join(HISTORY_FIELDS)


def _path_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _file_size(path):
    return os.stat(path)[6]


def _join_path(base, leaf):
    if base.endswith("/"):
        return base + leaf
    return base + "/" + leaf


def ensure_dir(path):
    if _path_exists(path):
        return

    parent = path.rsplit("/", 1)[0]
    if parent and parent != path and not _path_exists(parent):
        ensure_dir(parent)

    try:
        os.mkdir(path)
    except OSError:
        pass


def history_path_for_timestamp(root, timestamp_utc):
    day = timestamp_utc[:10]
    return _join_path(_join_path(root, "history"), day + ".csv")


def _format_csv_value(value):
    if value is None:
        return ""
    return str(value)


def format_history_row(record):
    return ",".join(_format_csv_value(record.get(field)) for field in HISTORY_FIELDS)


class StorageManager:
    def __init__(self, root="/sd", history_enabled=True):
        self.root = root
        self.history_enabled = history_enabled
        self.history_dir = _join_path(root, "history")
        self.queue_dir = _join_path(root, "queue")
        self.queue_path = _join_path(self.queue_dir, "pending.jsonl")
        self.state_path = _join_path(self.queue_dir, "state.json")

    def has_durable_storage(self):
        return bool(self.root) and _path_exists(self.root)

    def prepare(self):
        if not self.has_durable_storage():
            return False

        ensure_dir(self.history_dir)
        ensure_dir(self.queue_dir)
        return True

    def append_history(self, record):
        if not self.history_enabled or not self.prepare():
            return False

        path = history_path_for_timestamp(self.root, record["timestamp_utc"])
        write_header = (not _path_exists(path)) or (_file_size(path) == 0)

        with open(path, "a") as handle:
            if write_header:
                handle.write(HISTORY_HEADER + "\n")
            handle.write(format_history_row(record) + "\n")

        return True

    def append_queue(self, record):
        if not self.prepare():
            return False

        line = dumps_json(record)
        if not isinstance(line, (bytes, bytearray)):
            line = line.encode("utf-8")

        with open(self.queue_path, "ab") as handle:
            handle.write(line)
            handle.write(b"\n")

        return True

    def load_queue_offset(self):
        if not _path_exists(self.state_path):
            return 0

        with open(self.state_path, "r") as handle:
            data = json.loads(handle.read())
        return int(data.get("offset", 0))

    def mark_queue_offset(self, offset):
        if not self.prepare():
            return False

        with open(self.state_path, "w") as handle:
            handle.write(dumps_json({"offset": int(offset)}))

        return True

    def iter_pending(self, limit=None):
        if not _path_exists(self.queue_path):
            return

        offset = self.load_queue_offset()
        count = 0
        with open(self.queue_path, "rb") as handle:
            handle.seek(offset)
            while True:
                record_offset = handle.tell()
                line = handle.readline()
                if not line:
                    break

                next_offset = handle.tell()
                if not line.strip():
                    continue

                record = json.loads(line.decode("utf-8"))
                yield record_offset, next_offset, record

                count += 1
                if limit is not None and count >= limit:
                    break

    def compact_queue(self):
        if not self.has_durable_storage() or not _path_exists(self.queue_path):
            self.mark_queue_offset(0)
            return False

        offset = self.load_queue_offset()
        if offset <= 0:
            return False

        tmp_path = self.queue_path + ".tmp"
        with open(self.queue_path, "rb") as source:
            source.seek(offset)
            remaining = source.read()

        try:
            os.remove(tmp_path)
        except OSError:
            pass

        if remaining:
            with open(tmp_path, "wb") as target:
                target.write(remaining)

            try:
                os.remove(self.queue_path)
            except OSError:
                pass
            os.rename(tmp_path, self.queue_path)
        else:
            try:
                os.remove(self.queue_path)
            except OSError:
                pass

        self.mark_queue_offset(0)
        return True
