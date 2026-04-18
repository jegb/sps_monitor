try:
    import time
except ImportError:
    import utime as time

AHT10_I2C_ADDRESS = 0x38

CMD_INITIALIZE = 0xE1
CMD_TRIGGER_MEASUREMENT = 0xAC
CMD_SOFT_RESET = 0xBA
CMD_READ_STATUS = 0x71

INITIALIZE_ARG1 = 0x08
INITIALIZE_ARG2 = 0x00
TRIGGER_ARG1 = 0x33
TRIGGER_ARG2 = 0x00

STATUS_BUSY = 0x80
STATUS_CALIBRATED = 0x08


def _sleep_ms(delay_ms):
    if delay_ms <= 0:
        return

    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


def is_busy(status):
    return bool(status & STATUS_BUSY)


def is_calibrated(status):
    return bool(status & STATUS_CALIBRATED)


def parse_measurement_frame(raw_data):
    if len(raw_data) != 6:
        raise ValueError("AHT10 measurement frame must be exactly 6 bytes")

    status = raw_data[0]
    humidity_raw = (
        (raw_data[1] << 12)
        | (raw_data[2] << 4)
        | (raw_data[3] >> 4)
    )
    temperature_raw = (
        ((raw_data[3] & 0x0F) << 16)
        | (raw_data[4] << 8)
        | raw_data[5]
    )

    humidity_pct = humidity_raw * 100.0 / 1048576.0
    humidity_pct = min(100.0, max(0.0, humidity_pct))
    temperature_c = temperature_raw * 200.0 / 1048576.0 - 50.0

    return {
        "status": status,
        "humidity": round(humidity_pct, 4),
        "temperature": round(temperature_c, 4),
    }


class AHT10Sensor:
    def __init__(self, i2c, address=AHT10_I2C_ADDRESS):
        self.i2c = i2c
        self.address = address
        self._initialized = False

    def probe(self):
        return self.address in self.i2c.scan()

    def soft_reset(self):
        self.i2c.writeto(self.address, bytes((CMD_SOFT_RESET,)))
        _sleep_ms(20)
        self._initialized = False

    def _read_status(self):
        self.i2c.writeto(self.address, bytes((CMD_READ_STATUS,)))
        return self.i2c.readfrom(self.address, 1)[0]

    def _ensure_initialized(self):
        if self._initialized:
            return

        status = self._read_status()
        if not is_calibrated(status):
            self.i2c.writeto(
                self.address,
                bytes((CMD_INITIALIZE, INITIALIZE_ARG1, INITIALIZE_ARG2)),
            )
            _sleep_ms(10)
            status = self._read_status()

        if not is_calibrated(status):
            raise RuntimeError("AHT10 did not enter calibrated state")

        self._initialized = True

    def read_temperature_humidity(self):
        self._ensure_initialized()
        self.i2c.writeto(
            self.address,
            bytes((CMD_TRIGGER_MEASUREMENT, TRIGGER_ARG1, TRIGGER_ARG2)),
        )
        _sleep_ms(80)

        raw_data = self.i2c.readfrom(self.address, 6)
        for _ in range(5):
            if not is_busy(raw_data[0]):
                break
            _sleep_ms(10)
            raw_data = self.i2c.readfrom(self.address, 6)

        if is_busy(raw_data[0]):
            raise RuntimeError("AHT10 measurement did not complete")

        parsed = parse_measurement_frame(raw_data)
        return parsed["temperature"], parsed["humidity"]
