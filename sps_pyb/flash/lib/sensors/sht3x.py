try:
    import time
except ImportError:
    import utime as time

MEASURE_HIGH_REPEATABILITY = b"\x24\x00"


def _sleep_ms(delay_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


def calculate_crc(data):
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def parse_measurement(raw_data):
    if len(raw_data) != 6:
        raise ValueError("SHT3x frame must be exactly 6 bytes")

    temp_pair = raw_data[0:2]
    temp_crc = raw_data[2]
    humidity_pair = raw_data[3:5]
    humidity_crc = raw_data[5]

    if calculate_crc(temp_pair) != temp_crc:
        raise ValueError("CRC mismatch for temperature word")
    if calculate_crc(humidity_pair) != humidity_crc:
        raise ValueError("CRC mismatch for humidity word")

    raw_temp = (temp_pair[0] << 8) | temp_pair[1]
    raw_humidity = (humidity_pair[0] << 8) | humidity_pair[1]

    temperature_c = -45.0 + (175.0 * raw_temp / 65535.0)
    humidity_pct = 100.0 * raw_humidity / 65535.0
    return round(temperature_c, 2), round(humidity_pct, 2)


class SHT3XSensor:
    def __init__(self, i2c, address=0x44):
        self.i2c = i2c
        self.address = address

    def probe(self):
        return self.address in self.i2c.scan()

    def read_temperature_humidity(self):
        self.i2c.writeto(self.address, MEASURE_HIGH_REPEATABILITY)
        _sleep_ms(20)
        raw_data = self.i2c.readfrom(self.address, 6)
        return parse_measurement(raw_data)
