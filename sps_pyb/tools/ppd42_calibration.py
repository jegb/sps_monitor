"""Capture and fit PPD42 calibration data against MQTT reference payloads."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TARGET_FIELDS = ("pm_1_0", "pm_2_5", "pm_4_0", "pm_10_0")
DEFAULT_SAMPLE_FIELD = "ppd42_particle_count"
DEFAULT_MAX_TIMESTAMP_DRIFT_S = 24 * 60 * 60
DEFAULT_MULTIVARIATE_FIELDS = ("ppd42_particle_count", "temp", "humidity")


def parse_timestamp_utc(value: str | None, fallback: float) -> float:
    if not value:
        return float(fallback)


def parse_timestamp_optional(value: str | None) -> float | None:
    if not value:
        return None

    normalized = str(value).strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None

    normalized = str(value).strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return float(fallback)


def coerce_float(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def pair_payloads(
    sample_payload: dict[str, Any],
    reference_payload: dict[str, Any],
    *,
    sample_received_at: float,
    reference_received_at: float,
    max_skew_s: float,
    sample_field: str = DEFAULT_SAMPLE_FIELD,
    target_fields: tuple[str, ...] = DEFAULT_TARGET_FIELDS,
    max_timestamp_drift_s: float = DEFAULT_MAX_TIMESTAMP_DRIFT_S,
) -> dict[str, Any] | None:
    sample_value = coerce_float(sample_payload.get(sample_field))
    if sample_value is None:
        return None

    sample_timestamp = parse_timestamp_optional(sample_payload.get("timestamp_utc"))
    reference_timestamp = parse_timestamp_optional(reference_payload.get("timestamp_utc"))

    use_payload_timestamps = (
        sample_timestamp is not None
        and reference_timestamp is not None
        and abs(sample_timestamp - float(sample_received_at)) <= float(max_timestamp_drift_s)
        and abs(reference_timestamp - float(reference_received_at)) <= float(max_timestamp_drift_s)
    )

    if use_payload_timestamps:
        sample_event_time = float(sample_timestamp)
        reference_event_time = float(reference_timestamp)
    else:
        sample_event_time = float(sample_received_at)
        reference_event_time = float(reference_received_at)

    pair_age_s = abs(sample_event_time - reference_event_time)
    if pair_age_s > float(max_skew_s):
        return None

    row = {
        "sample_received_at": round(float(sample_received_at), 4),
        "reference_received_at": round(float(reference_received_at), 4),
        "sample_timestamp_utc": sample_payload.get("timestamp_utc", ""),
        "reference_timestamp_utc": reference_payload.get("timestamp_utc", ""),
        "pair_age_s": round(pair_age_s, 4),
        sample_field: sample_value,
        "temp": coerce_float(sample_payload.get("temp")),
        "humidity": coerce_float(sample_payload.get("humidity")),
    }

    for field_name in target_fields:
        row[field_name] = coerce_float(reference_payload.get(field_name))

    return row


def fit_linear_model(samples: list[tuple[float, float]]) -> dict[str, float]:
    if len(samples) < 2:
        raise ValueError("At least two samples are required")

    xs = [float(x) for x, _ in samples]
    ys = [float(y) for _, y in samples]

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    if ss_xx == 0.0:
        raise ValueError("All sample x values are identical")

    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    a = ss_xy / ss_xx
    b = mean_y - (a * mean_x)

    predictions = [(a * x) + b for x in xs]
    ss_res = sum((y - y_hat) ** 2 for y, y_hat in zip(ys, predictions))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - (ss_res / ss_tot)

    return {
        "a": round(a, 8),
        "b": round(b, 8),
        "r2": round(r2, 6),
        "samples": len(samples),
    }


def solve_linear_system(
    matrix: list[list[float]],
    vector: list[float],
) -> list[float]:
    size = len(matrix)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for pivot_index in range(size):
        pivot_row = max(
            range(pivot_index, size),
            key=lambda row_index: abs(augmented[row_index][pivot_index]),
        )
        if abs(augmented[pivot_row][pivot_index]) < 1e-12:
            raise ValueError("Singular matrix")
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = (
                augmented[pivot_row],
                augmented[pivot_index],
            )

        pivot = augmented[pivot_index][pivot_index]
        for column_index in range(pivot_index, size + 1):
            augmented[pivot_index][column_index] /= pivot

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            if factor == 0.0:
                continue
            for column_index in range(pivot_index, size + 1):
                augmented[row_index][column_index] -= (
                    factor * augmented[pivot_index][column_index]
                )

    return [augmented[row_index][size] for row_index in range(size)]


def fit_multivariate_linear_model(
    samples: list[tuple[list[float], float]],
    *,
    predictor_names: tuple[str, ...],
) -> dict[str, Any]:
    if len(samples) < 2:
        raise ValueError("At least two samples are required")

    num_predictors = len(predictor_names)
    if num_predictors == 0:
        raise ValueError("At least one predictor is required")

    features = [[1.0, *[float(value) for value in feature_row]] for feature_row, _ in samples]
    targets = [float(target) for _, target in samples]

    num_coefficients = num_predictors + 1
    xtx = [[0.0 for _ in range(num_coefficients)] for _ in range(num_coefficients)]
    xty = [0.0 for _ in range(num_coefficients)]

    for feature_row, target in zip(features, targets):
        for row_index in range(num_coefficients):
            xty[row_index] += feature_row[row_index] * target
            for column_index in range(num_coefficients):
                xtx[row_index][column_index] += (
                    feature_row[row_index] * feature_row[column_index]
                )

    coefficients = solve_linear_system(xtx, xty)
    intercept = coefficients[0]
    predictor_coefficients = coefficients[1:]

    predictions = []
    for feature_row in features:
        prediction = sum(
            coefficient * value
            for coefficient, value in zip(coefficients, feature_row)
        )
        predictions.append(prediction)

    mean_y = sum(targets) / len(targets)
    ss_res = sum((actual - predicted) ** 2 for actual, predicted in zip(targets, predictions))
    ss_tot = sum((actual - mean_y) ** 2 for actual in targets)
    r2 = 1.0 if ss_tot == 0.0 else 1.0 - (ss_res / ss_tot)

    return {
        "intercept": round(intercept, 8),
        "coefficients": {
            name: round(value, 8)
            for name, value in zip(predictor_names, predictor_coefficients)
        },
        "r2": round(r2, 6),
        "samples": len(samples),
    }


def fit_models(
    rows: list[dict[str, Any]],
    *,
    sample_field: str = DEFAULT_SAMPLE_FIELD,
    target_fields: tuple[str, ...] = DEFAULT_TARGET_FIELDS,
) -> dict[str, dict[str, float]]:
    models: dict[str, dict[str, float]] = {}

    for field_name in target_fields:
        samples: list[tuple[float, float]] = []
        for row in rows:
            x = coerce_float(row.get(sample_field))
            y = coerce_float(row.get(field_name))
            if x is None or y is None:
                continue
            samples.append((x, y))

        if len(samples) >= 2:
            models[field_name] = fit_linear_model(samples)

    return models


def fit_multivariate_models(
    rows: list[dict[str, Any]],
    *,
    predictor_fields: tuple[str, ...] = DEFAULT_MULTIVARIATE_FIELDS,
    target_fields: tuple[str, ...] = DEFAULT_TARGET_FIELDS,
) -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}

    for field_name in target_fields:
        samples: list[tuple[list[float], float]] = []
        for row in rows:
            predictors: list[float] = []
            skip_row = False
            for predictor_name in predictor_fields:
                value = coerce_float(row.get(predictor_name))
                if value is None:
                    skip_row = True
                    break
                predictors.append(value)

            target_value = coerce_float(row.get(field_name))
            if skip_row or target_value is None:
                continue

            samples.append((predictors, target_value))

        if len(samples) >= 2:
            models[field_name] = fit_multivariate_linear_model(
                samples,
                predictor_names=predictor_fields,
            )

    return models


def model_config_snippet(models: dict[str, dict[str, float]]) -> str:
    lines = ["PPD42_LINEAR_PM_CALIBRATION = {"]
    for field_name in DEFAULT_TARGET_FIELDS:
        model = models.get(field_name)
        if model is None:
            continue
        lines.append(
            "    %r: {\"a\": %s, \"b\": %s},"
            % (field_name, model["a"], model["b"])
        )
    lines.append("}")
    return "\n".join(lines)


def multivariate_model_config_snippet(models: dict[str, dict[str, Any]]) -> str:
    lines = ["PPD42_MULTIVARIATE_PM_CALIBRATION = {"]
    for field_name in DEFAULT_TARGET_FIELDS:
        model = models.get(field_name)
        if model is None:
            continue
        coeffs = ", ".join(
            f'"{name}": {value}'
            for name, value in model["coefficients"].items()
        )
        lines.append(
            '    %r: {"intercept": %s, "coefficients": {%s}},'
            % (field_name, model["intercept"], coeffs)
        )
    lines.append("}")
    return "\n".join(lines)


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _topic_header_fields(sample_field: str, target_fields: tuple[str, ...]) -> list[str]:
    return [
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


def run_capture(args: argparse.Namespace) -> int:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise SystemExit(
            "paho-mqtt is required for capture mode. Install it with: pip install paho-mqtt"
        ) from exc

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sample_topic = args.sample_topic
    reference_topic = args.reference_topic
    target_fields = tuple(args.target_fields.split(","))
    header = _topic_header_fields(args.sample_field, target_fields)

    state = {
        "sample": None,
        "reference": None,
        "sample_seq": 0,
        "reference_seq": 0,
        "last_emitted": None,
        "captured": 0,
    }

    done = False
    started_at = time.time()

    if output_path.exists() and output_path.stat().st_size > 0:
        append_header = False
    else:
        append_header = True

    with output_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        if append_header:
            writer.writeheader()

        def maybe_emit_pair() -> None:
            sample_event = state["sample"]
            reference_event = state["reference"]
            if sample_event is None or reference_event is None:
                return

            pair_key = (state["sample_seq"], state["reference_seq"])
            if pair_key == state["last_emitted"]:
                return

            row = pair_payloads(
                sample_event["payload"],
                reference_event["payload"],
                sample_received_at=sample_event["received_at"],
                reference_received_at=reference_event["received_at"],
                max_skew_s=args.max_skew_s,
                sample_field=args.sample_field,
                target_fields=target_fields,
            )
            if row is None:
                return

            writer.writerow(row)
            handle.flush()
            state["last_emitted"] = pair_key
            state["captured"] += 1
            print(
                "captured pair #%s: %s=%s, pm_2_5=%s"
                % (
                    state["captured"],
                    args.sample_field,
                    row.get(args.sample_field),
                    row.get("pm_2_5"),
                )
            )

        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                print("mqtt: connect failed with code %s" % rc)
                return
            client.subscribe(sample_topic, qos=0)
            client.subscribe(reference_topic, qos=0)
            print("mqtt: subscribed to %s and %s" % (sample_topic, reference_topic))

        def on_message(client, userdata, msg):
            payload = json.loads(msg.payload.decode("utf-8"))
            event = {
                "payload": payload,
                "received_at": time.time(),
            }

            if msg.topic == sample_topic:
                state["sample"] = event
                state["sample_seq"] += 1
            elif msg.topic == reference_topic:
                state["reference"] = event
                state["reference_seq"] += 1
            maybe_emit_pair()

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(args.broker_host, args.broker_port, 60)
        client.loop_start()

        try:
            while True:
                if args.max_pairs and state["captured"] >= args.max_pairs:
                    break
                if args.duration_s and (time.time() - started_at) >= args.duration_s:
                    break
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()

    print("capture complete: %s paired rows written to %s" % (state["captured"], output_path))
    return 0


def run_fit(args: argparse.Namespace) -> int:
    target_fields = tuple(args.target_fields.split(","))
    rows = load_rows(args.input)
    models = fit_models(
        rows,
        sample_field=args.sample_field,
        target_fields=target_fields,
    )

    result = {
        "sample_field": args.sample_field,
        "target_fields": target_fields,
        "models": models,
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    print()
    print(model_config_snippet(models))
    return 0


def run_fit_multi(args: argparse.Namespace) -> int:
    predictor_fields = tuple(args.predictor_fields.split(","))
    target_fields = tuple(args.target_fields.split(","))
    rows = load_rows(args.input)
    models = fit_multivariate_models(
        rows,
        predictor_fields=predictor_fields,
        target_fields=target_fields,
    )

    result = {
        "predictor_fields": predictor_fields,
        "target_fields": target_fields,
        "models": models,
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    print()
    print(multivariate_model_config_snippet(models))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="Capture paired MQTT calibration rows")
    capture.add_argument("--broker-host", required=True)
    capture.add_argument("--broker-port", type=int, default=1883)
    capture.add_argument("--sample-topic", required=True)
    capture.add_argument("--reference-topic", required=True)
    capture.add_argument("--output", required=True)
    capture.add_argument("--sample-field", default=DEFAULT_SAMPLE_FIELD)
    capture.add_argument("--target-fields", default=",".join(DEFAULT_TARGET_FIELDS))
    capture.add_argument("--max-skew-s", type=float, default=45.0)
    capture.add_argument("--max-pairs", type=int, default=0)
    capture.add_argument("--duration-s", type=float, default=0.0)
    capture.set_defaults(func=run_capture)

    fit = subparsers.add_parser("fit", help="Fit linear PM models from captured CSV")
    fit.add_argument("--input", required=True)
    fit.add_argument("--sample-field", default=DEFAULT_SAMPLE_FIELD)
    fit.add_argument("--target-fields", default=",".join(DEFAULT_TARGET_FIELDS))
    fit.set_defaults(func=run_fit)

    fit_multi = subparsers.add_parser(
        "fit-multi",
        help="Fit multivariate PM models from captured CSV",
    )
    fit_multi.add_argument("--input", required=True)
    fit_multi.add_argument(
        "--predictor-fields",
        default=",".join(DEFAULT_MULTIVARIATE_FIELDS),
    )
    fit_multi.add_argument("--target-fields", default=",".join(DEFAULT_TARGET_FIELDS))
    fit_multi.set_defaults(func=run_fit_multi)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
