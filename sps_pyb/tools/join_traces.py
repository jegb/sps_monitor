"""Join two JSONL MQTT traces into a paired PPD42 calibration CSV."""

from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_left
from pathlib import Path
from typing import Any

from sps_pyb.tools.mqtt_trace import RESERVED_FIELDS, decode_payload
from sps_pyb.tools.ppd42_calibration import (
    DEFAULT_SAMPLE_FIELD,
    DEFAULT_TARGET_FIELDS,
    pair_payloads,
)


def load_jsonl_records(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def extract_payload(record: dict[str, Any]) -> dict[str, Any] | None:
    raw_payload = record.get("raw_payload")
    if isinstance(raw_payload, str) and raw_payload:
        payload = decode_payload(raw_payload)
        if isinstance(payload, dict):
            return payload

    payload: dict[str, Any] = {}
    for key, value in record.items():
        if key in RESERVED_FIELDS:
            continue
        if key.startswith("payload_"):
            payload[key[len("payload_") :]] = value
            continue
        payload[key] = value

    return payload or None


def build_topic_events(
    records: list[dict[str, Any]],
    *,
    topic: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for record in records:
        if record.get("mqtt_topic") != topic:
            continue

        received_at = record.get("received_at")
        try:
            received_at_value = float(received_at)
        except (TypeError, ValueError):
            continue

        payload = extract_payload(record)
        if not isinstance(payload, dict):
            continue

        events.append(
            {
                "received_at": received_at_value,
                "payload": payload,
            }
        )

    events.sort(key=lambda event: event["received_at"])
    return events


def find_nearest_event(
    events: list[dict[str, Any]],
    *,
    received_at: float,
) -> dict[str, Any] | None:
    if not events:
        return None

    timestamps = [float(event["received_at"]) for event in events]
    index = bisect_left(timestamps, float(received_at))

    candidates: list[dict[str, Any]] = []
    if index < len(events):
        candidates.append(events[index])
    if index > 0:
        candidates.append(events[index - 1])

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda event: abs(float(event["received_at"]) - float(received_at)),
    )


def join_events(
    sample_events: list[dict[str, Any]],
    reference_events: list[dict[str, Any]],
    *,
    sample_field: str = DEFAULT_SAMPLE_FIELD,
    target_fields: tuple[str, ...] = DEFAULT_TARGET_FIELDS,
    max_skew_s: float = 45.0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for sample_event in sample_events:
        reference_event = find_nearest_event(
            reference_events,
            received_at=float(sample_event["received_at"]),
        )
        if reference_event is None:
            continue

        row = pair_payloads(
            sample_event["payload"],
            reference_event["payload"],
            sample_received_at=float(sample_event["received_at"]),
            reference_received_at=float(reference_event["received_at"]),
            max_skew_s=max_skew_s,
            sample_field=sample_field,
            target_fields=target_fields,
        )
        if row is not None:
            rows.append(row)

    return rows


def write_rows_csv(
    rows: list[dict[str, Any]],
    *,
    output: str | Path,
    sample_field: str,
    target_fields: tuple[str, ...],
) -> None:
    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_received_at",
        "reference_received_at",
        "sample_timestamp_utc",
        "reference_timestamp_utc",
        "pair_age_s",
        sample_field,
        "temp",
        "humidity",
        *target_fields,
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_join(args: argparse.Namespace) -> int:
    target_fields = tuple(args.target_fields.split(","))

    sample_records = load_jsonl_records(args.sample_input)
    reference_records = load_jsonl_records(args.reference_input)

    sample_events = build_topic_events(sample_records, topic=args.sample_topic)
    reference_events = build_topic_events(reference_records, topic=args.reference_topic)

    rows = join_events(
        sample_events,
        reference_events,
        sample_field=args.sample_field,
        target_fields=target_fields,
        max_skew_s=args.max_skew_s,
    )

    write_rows_csv(
        rows,
        output=args.output,
        sample_field=args.sample_field,
        target_fields=target_fields,
    )

    print(
        "join complete: %s rows written to %s"
        % (len(rows), Path(args.output).expanduser())
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-input", required=True)
    parser.add_argument("--reference-input", required=True)
    parser.add_argument("--sample-topic", default="airquality/sensor_ppd42_raw")
    parser.add_argument("--reference-topic", default="airquality/sensor")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-field", default=DEFAULT_SAMPLE_FIELD)
    parser.add_argument("--target-fields", default=",".join(DEFAULT_TARGET_FIELDS))
    parser.add_argument("--max-skew-s", type=float, default=45.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_join(args)


if __name__ == "__main__":
    raise SystemExit(main())
