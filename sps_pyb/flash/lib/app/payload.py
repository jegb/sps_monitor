try:
    import json
except ImportError:
    import ujson as json

PAYLOAD_FIELDS = (
    "pm_1_0",
    "pm_2_5",
    "pm_4_0",
    "pm_10_0",
    "temp",
    "humidity",
)
PM_FIELDS = PAYLOAD_FIELDS[:4]
OPTIONAL_PAYLOAD_FIELDS = (
    "ppd42_particle_count",
    "ppd42_particle_size",
)
CALIBRATION_PAYLOAD_FIELDS = (
    "timestamp_utc",
    "ppd42_particle_count",
    "ppd42_particle_size",
    "temp",
    "humidity",
)


def _round_value(value, digits=4):
    if value is None:
        return None
    return round(float(value), digits)


def build_sensor_record(
    timestamp_utc,
    pm_data,
    temp,
    humidity,
    pm_fields=None,
    ppd42_particle_count=None,
    ppd42_particle_size=None,
):
    record = {
        "timestamp_utc": timestamp_utc,
        "pm_1_0": _round_value(None if pm_data is None else pm_data["mc_1p0"]),
        "pm_2_5": _round_value(None if pm_data is None else pm_data["mc_2p5"]),
        "pm_4_0": _round_value(None if pm_data is None else pm_data["mc_4p0"]),
        "pm_10_0": _round_value(None if pm_data is None else pm_data["mc_10p0"]),
        "temp": _round_value(temp),
        "humidity": _round_value(humidity),
        "ppd42_particle_count": _round_value(ppd42_particle_count),
        "ppd42_particle_size": _round_value(ppd42_particle_size),
    }

    if pm_fields:
        for field_name in PM_FIELDS:
            if field_name in pm_fields:
                record[field_name] = _round_value(pm_fields[field_name])

    return record


def build_live_payload(record):
    payload = {field: record.get(field) for field in PAYLOAD_FIELDS}
    for field in OPTIONAL_PAYLOAD_FIELDS:
        if record.get(field) is not None:
            payload[field] = record.get(field)
    return payload


def build_mqtt_payload(
    record,
    *,
    include_optional_fields=True,
    drop_null_fields=False,
):
    payload = {}

    for field in PAYLOAD_FIELDS:
        value = record.get(field)
        if drop_null_fields and value is None:
            continue
        payload[field] = value

    if include_optional_fields:
        for field in OPTIONAL_PAYLOAD_FIELDS:
            value = record.get(field)
            if value is not None:
                payload[field] = value

    return payload


def build_calibration_payload(record):
    payload = {}
    for field in CALIBRATION_PAYLOAD_FIELDS:
        value = record.get(field)
        if value is None and field != "timestamp_utc":
            continue
        payload[field] = value
    return payload


def dumps_json(value):
    return json.dumps(value)
