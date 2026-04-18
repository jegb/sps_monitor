try:
    import dht
except ImportError:
    dht = None

try:
    from machine import Pin
except ImportError:
    Pin = None

try:
    import time
except ImportError:
    import utime as time


def _sleep_ms(delay_ms):
    if delay_ms <= 0:
        return

    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(current, previous):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(current, previous)
    return current - previous


class DHT11Sensor:
    def __init__(self, pin):
        self.pin = pin
        self._sensor = None
        self._last_measure_ms = None

    def _get_sensor(self):
        if dht is None:
            raise RuntimeError("dht module is unavailable in this firmware")
        if Pin is None:
            raise RuntimeError("machine.Pin is unavailable in this runtime")

        if self._sensor is None:
            self._sensor = dht.DHT11(Pin(self.pin))

        return self._sensor

    def probe(self):
        try:
            self.read_temperature_humidity()
            return True
        except Exception:
            return False

    def read_temperature_humidity(self):
        sensor = self._get_sensor()
        now_ms = _ticks_ms()
        if self._last_measure_ms is not None:
            elapsed_ms = _ticks_diff(now_ms, self._last_measure_ms)
            if elapsed_ms < 1000:
                _sleep_ms(1000 - elapsed_ms)
        sensor.measure()
        self._last_measure_ms = _ticks_ms()
        return float(sensor.temperature()), float(sensor.humidity())
