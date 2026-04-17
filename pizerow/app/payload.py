import json

PAYLOAD_FIELDS = (
    "pm_1_0",
    "pm_2_5",
    "pm_4_0",
    "pm_10_0",
    "temp",
    "humidity",
)


def _round_value(value, digits=1):
    if value is None:
        return None
    return round(float(value), digits)


def build_sensor_record(timestamp_utc, pm_data, temp, humidity):
    if pm_data is None:
        raise ValueError("pm_data is required")

    return {
        "timestamp_utc": timestamp_utc,
        "pm_1_0": _round_value(pm_data["mc_1p0"]),
        "pm_2_5": _round_value(pm_data["mc_2p5"]),
        "pm_4_0": _round_value(pm_data["mc_4p0"]),
        "pm_10_0": _round_value(pm_data["mc_10p0"]),
        "temp": _round_value(temp),
        "humidity": _round_value(humidity),
    }


def build_live_payload(record):
    return {field: record.get(field) for field in PAYLOAD_FIELDS}


def dumps_json(value):
    return json.dumps(value, separators=(",", ":"))
