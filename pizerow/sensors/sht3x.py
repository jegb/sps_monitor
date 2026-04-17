import time

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    SMBus = None
    i2c_msg = None

MEASURE_HIGH_REPEATABILITY = b"\x24\x00"


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
        raise ValueError("CRC mismatch for temperature")
    if calculate_crc(humidity_pair) != humidity_crc:
        raise ValueError("CRC mismatch for humidity")

    raw_temp = (temp_pair[0] << 8) | temp_pair[1]
    raw_humidity = (humidity_pair[0] << 8) | humidity_pair[1]

    temperature_c = -45.0 + (175.0 * raw_temp / 65535.0)
    humidity_pct = 100.0 * raw_humidity / 65535.0
    return round(temperature_c, 2), round(humidity_pct, 2)


class SHT3XSensor:
    def __init__(self, bus_num=1, address=0x44):
        self.bus_num = int(bus_num)
        self.address = int(address)

    def _ensure_smbus(self):
        if SMBus is None or i2c_msg is None:
            raise RuntimeError("smbus2 is not installed")

    def probe(self):
        try:
            self.read_temperature_humidity()
            return True
        except Exception:
            return False

    def read_temperature_humidity(self):
        self._ensure_smbus()

        with SMBus(self.bus_num) as bus:
            bus.i2c_rdwr(i2c_msg.write(self.address, MEASURE_HIGH_REPEATABILITY))
            time.sleep(0.02)
            read_msg = i2c_msg.read(self.address, 6)
            bus.i2c_rdwr(read_msg)
            return parse_measurement(bytes(read_msg))
