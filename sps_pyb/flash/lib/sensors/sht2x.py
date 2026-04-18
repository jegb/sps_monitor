try:
    import time
except ImportError:
    import utime as time

SHT2X_I2C_ADDRESS = 0x40

CMD_TRIGGER_T_MEAS_NO_HOLD = 0xF3
CMD_TRIGGER_RH_MEAS_NO_HOLD = 0xF5
CMD_SOFT_RESET = 0xFE


def _sleep_ms(delay_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


def calculate_crc(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x131) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def parse_temperature(raw_data):
    if len(raw_data) != 3:
        raise ValueError("SHT2x temperature frame must be exactly 3 bytes")

    payload = raw_data[0:2]
    if calculate_crc(payload) != raw_data[2]:
        raise ValueError("CRC mismatch for SHT2x temperature")

    raw_temp = ((payload[0] << 8) | payload[1]) & 0xFFFC
    temperature_c = -46.85 + (175.72 * raw_temp / 65536.0)
    return round(temperature_c, 4)


def parse_humidity(raw_data):
    if len(raw_data) != 3:
        raise ValueError("SHT2x humidity frame must be exactly 3 bytes")

    payload = raw_data[0:2]
    if calculate_crc(payload) != raw_data[2]:
        raise ValueError("CRC mismatch for SHT2x humidity")

    raw_humidity = ((payload[0] << 8) | payload[1]) & 0xFFFC
    humidity_pct = -6.0 + (125.0 * raw_humidity / 65536.0)
    humidity_pct = min(100.0, max(0.0, humidity_pct))
    return round(humidity_pct, 4)


class SHT2XSensor:
    def __init__(self, i2c, address=SHT2X_I2C_ADDRESS):
        self.i2c = i2c
        self.address = address

    def probe(self):
        return self.address in self.i2c.scan()

    def soft_reset(self):
        self.i2c.writeto(self.address, bytes((CMD_SOFT_RESET,)))
        _sleep_ms(15)

    def _read_frame(self, command, wait_ms):
        self.i2c.writeto(self.address, bytes((command,)))
        _sleep_ms(wait_ms)
        return self.i2c.readfrom(self.address, 3)

    def read_temperature_humidity(self):
        temperature = parse_temperature(
            self._read_frame(CMD_TRIGGER_T_MEAS_NO_HOLD, 90)
        )
        humidity = parse_humidity(
            self._read_frame(CMD_TRIGGER_RH_MEAS_NO_HOLD, 30)
        )
        return temperature, humidity
