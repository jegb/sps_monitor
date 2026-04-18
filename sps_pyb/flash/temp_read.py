import sys

try:
    import time
except ImportError:
    import utime as time


def _add_lib_path(path):
    if path not in sys.path:
        sys.path.append(path)


_add_lib_path("/flash/lib")
_add_lib_path("lib")

try:
    import config
except ImportError as exc:
    raise SystemExit("Missing config.py on the board filesystem") from exc

try:
    from sensors.aht10 import AHT10Sensor
    from sensors.dht11 import DHT11Sensor
    from sensors.sht2x import SHT2XSensor
    from sensors.sht3x import SHT3XSensor
except ImportError:
    from sps_pyb.flash.lib.sensors.aht10 import AHT10Sensor
    from sps_pyb.flash.lib.sensors.dht11 import DHT11Sensor
    from sps_pyb.flash.lib.sensors.sht2x import SHT2XSensor
    from sps_pyb.flash.lib.sensors.sht3x import SHT3XSensor


def _sleep_seconds(seconds):
    if seconds <= 0:
        return

    if hasattr(time, "sleep"):
        time.sleep(seconds)
    else:
        time.sleep_ms(int(seconds * 1000))


def _create_i2c():
    from machine import I2C

    bus = getattr(config, "I2C_BUS", "X")
    freq = int(getattr(config, "I2C_FREQ", 100000))

    try:
        return I2C(bus, freq=freq)
    except TypeError:
        return I2C(int(bus), freq=freq)


def _env_sensor_kind():
    kind = str(getattr(config, "ENV_SENSOR", "")).strip().lower()
    if kind:
        return kind

    if bool(getattr(config, "SHT3X_ENABLED", True)):
        return "sht3x"
    return "none"


def _create_sensor():
    kind = _env_sensor_kind()
    if kind in ("", "none", "off"):
        raise ValueError("ENV_SENSOR is disabled; choose sht3x, sht20, or dht11")

    if kind == "sht3x":
        sensor = SHT3XSensor(
            _create_i2c(),
            address=int(getattr(config, "SHT3X_ADDR", 0x44)),
        )
        return kind, sensor

    if kind == "sht20":
        sensor = SHT2XSensor(
            _create_i2c(),
            address=int(getattr(config, "SHT20_ADDR", 0x40)),
        )
        return kind, sensor

    if kind == "aht10":
        sensor = AHT10Sensor(
            _create_i2c(),
            address=int(getattr(config, "AHT10_ADDR", 0x38)),
        )
        return kind, sensor

    if kind == "dht11":
        sensor = DHT11Sensor(
            pin=getattr(config, "DHT11_PIN", "X1"),
        )
        return kind, sensor

    raise ValueError("Unsupported ENV_SENSOR: %s" % kind)


def _read(kind, sensor):
    temperature, humidity = sensor.read_temperature_humidity()
    payload = {
        "sensor": kind,
        "temp": round(float(temperature), 4),
        "humidity": round(float(humidity), 4),
    }
    print(payload)
    return payload


def run_once():
    kind, sensor = _create_sensor()
    return _read(kind, sensor)


def run(interval_s=None, count=0):
    interval_s = int(
        getattr(config, "PUBLISH_INTERVAL_S", 60)
        if interval_s is None
        else interval_s
    )
    count = int(count)
    kind, sensor = _create_sensor()
    seen = 0

    while True:
        _read(kind, sensor)
        seen += 1
        if count and seen >= count:
            return
        _sleep_seconds(interval_s)


if __name__ == "__main__":
    run_once()
