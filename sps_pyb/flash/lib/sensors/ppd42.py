try:
    import time
except ImportError:
    import utime as time

try:
    from machine import Pin
except ImportError:
    Pin = None

DEFAULT_PARTICLE_SIZE = 2.5
DEFAULT_SAMPLE_DURATION = 30


def _ticks_us():
    if hasattr(time, "ticks_us"):
        return time.ticks_us()
    return int(time.time() * 1000000)


def _ticks_diff(current, previous):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(current, previous)
    return current - previous


def _sleep_ms(delay_ms):
    if delay_ms <= 0:
        return

    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


def concentration_from_low_occupancy(low_occupancy_us, sample_duration_s):
    if sample_duration_s <= 0:
        raise ValueError("sample_duration_s must be positive")

    ratio = float(low_occupancy_us) / (float(sample_duration_s) * 1000000.0)
    return round(ratio * 1000.0, 4)


class PPD42Sensor:
    def __init__(self, pin="X2", particle_size=DEFAULT_PARTICLE_SIZE):
        if Pin is None:
            raise RuntimeError("machine.Pin is unavailable in this runtime")

        self.pin_name = pin
        self.particle_size = float(particle_size)
        self.pin = Pin(pin, Pin.IN)
        self._sampling = False
        self._low_started_us = None
        self._low_occupancy_us = 0
        self._irq = self.pin.irq(
            trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
            handler=self._edge_callback,
        )

    def _edge_callback(self, pin):
        if not self._sampling:
            return

        now_us = _ticks_us()
        if pin.value() == 0:
            self._low_started_us = now_us
            return

        if self._low_started_us is not None:
            self._low_occupancy_us += max(0, _ticks_diff(now_us, self._low_started_us))
            self._low_started_us = None

    def _start_sample(self):
        self._low_occupancy_us = 0
        self._sampling = True
        if self.pin.value() == 0:
            self._low_started_us = _ticks_us()
        else:
            self._low_started_us = None

    def _finish_sample(self):
        if self._sampling and self._low_started_us is not None and self.pin.value() == 0:
            self._low_occupancy_us += max(0, _ticks_diff(_ticks_us(), self._low_started_us))

        self._sampling = False
        self._low_started_us = None
        return self._low_occupancy_us

    def get_reading(self, sample_duration=DEFAULT_SAMPLE_DURATION):
        sample_duration = int(sample_duration)
        if sample_duration <= 0:
            raise ValueError("sample_duration must be positive")

        self._start_sample()
        remaining_ms = sample_duration * 1000
        while remaining_ms > 0:
            chunk_ms = 250 if remaining_ms > 250 else remaining_ms
            _sleep_ms(chunk_ms)
            remaining_ms -= chunk_ms

        low_occupancy_us = self._finish_sample()
        particle_count = concentration_from_low_occupancy(
            low_occupancy_us,
            sample_duration,
        )
        return {
            "particle_count": particle_count,
            "particle_size": self.particle_size,
            "low_occupancy_us": low_occupancy_us,
            "unit": "pcs/0.01cf",
        }
