"""Capture a single MQTT topic into JSONL for later offline joining."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESERVED_FIELDS = {
    "received_at",
    "received_at_iso",
    "mqtt_topic",
    "message_type",
    "message_value",
    "selected_field",
    "selected_value",
    "raw_payload",
}


def format_timestamp(received_at: float) -> str:
    """Return an ISO-8601 UTC timestamp string for a host receive time."""
    return (
        datetime.fromtimestamp(float(received_at), tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def coerce_float(value: Any) -> float | None:
    """Return a float for numeric-like values, otherwise ``None``."""
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def select_numeric_field(
    payload: dict[str, Any],
    *,
    preferred_field: str | None = None,
    previous_field: str | None = None,
) -> tuple[str | None, float | None]:
    """Select a representative numeric field from a payload."""
    if preferred_field:
        preferred_value = coerce_float(payload.get(preferred_field))
        if preferred_value is not None:
            return preferred_field, preferred_value

    if previous_field:
        previous_value = coerce_float(payload.get(previous_field))
        if previous_value is not None:
            return previous_field, previous_value

    for field_name, value in payload.items():
        numeric_value = coerce_float(value)
        if numeric_value is not None:
            return str(field_name), numeric_value

    return None, None


def normalize_field_name(name: str) -> str:
    """Avoid collisions between payload keys and recorder metadata."""
    if name in RESERVED_FIELDS:
        return f"payload_{name}"
    return name


def decode_payload(raw_payload: str) -> Any:
    """Decode a raw MQTT payload string into JSON or a scalar."""
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        numeric = coerce_float(raw_payload)
        return numeric if numeric is not None else raw_payload


def build_trace_record(
    *,
    topic: str,
    received_at: float,
    raw_payload: str,
    payload: Any,
    preferred_field: str | None = None,
    previous_field: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Build a JSONL-friendly MQTT trace record."""
    record: dict[str, Any] = {
        "received_at": float(received_at),
        "received_at_iso": format_timestamp(received_at),
        "mqtt_topic": topic,
        "raw_payload": raw_payload,
        "selected_field": None,
        "selected_value": None,
    }

    next_previous_field = previous_field

    if isinstance(payload, dict):
        selected_field, selected_value = select_numeric_field(
            payload,
            preferred_field=preferred_field,
            previous_field=previous_field,
        )
        record["message_type"] = "json_object"
        record["selected_field"] = selected_field
        record["selected_value"] = selected_value
        for key, value in payload.items():
            record[normalize_field_name(str(key))] = value
        next_previous_field = selected_field
    else:
        record["message_type"] = "scalar"
        record["message_value"] = payload
        scalar_value = coerce_float(payload)
        if scalar_value is not None:
            record["selected_value"] = scalar_value

    return record, next_previous_field


def run_capture(args: argparse.Namespace) -> int:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit(
            "paho-mqtt is required for mqtt_trace. Install it with: pip install paho-mqtt"
        ) from exc

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "w" if args.truncate else "a"
    state = {
        "count": 0,
        "selected_field": None,
    }
    started_at = time.time()

    with output_path.open(mode, encoding="utf-8") as handle:
        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                print("mqtt: connect failed with code %s" % rc)
                return
            client.subscribe(args.topic, qos=args.qos)
            print("mqtt: subscribed to %s" % args.topic)

        def on_message(client, userdata, msg):
            raw_payload = msg.payload.decode("utf-8")
            payload = decode_payload(raw_payload)
            received_at = time.time()
            record, next_field = build_trace_record(
                topic=msg.topic,
                received_at=received_at,
                raw_payload=raw_payload,
                payload=payload,
                preferred_field=args.preferred_field,
                previous_field=state["selected_field"],
            )
            state["selected_field"] = next_field
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")
            handle.flush()
            state["count"] += 1

            print(
                "captured message #%s on %s (selected=%s)"
                % (
                    state["count"],
                    msg.topic,
                    record.get("selected_field") or record.get("message_type"),
                )
            )

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(args.broker_host, args.broker_port, 60)
        client.loop_start()

        try:
            while True:
                if args.max_messages and state["count"] >= args.max_messages:
                    break
                if args.duration_s and (time.time() - started_at) >= args.duration_s:
                    break
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()

    print("trace complete: %s messages written to %s" % (state["count"], output_path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-host", required=True)
    parser.add_argument("--broker-port", type=int, default=1883)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--qos", type=int, default=0)
    parser.add_argument("--preferred-field")
    parser.add_argument("--max-messages", type=int, default=0)
    parser.add_argument("--duration-s", type=float, default=0.0)
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Overwrite the output file instead of appending",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_capture(args)


if __name__ == "__main__":
    raise SystemExit(main())
