try:
    import struct
except ImportError:
    import ustruct as struct

try:
    import time
except ImportError:
    import utime as time

SPS30_I2C_ADDRESS = 0x69

CMD_START_MEASUREMENT = 0x0010
CMD_STOP_MEASUREMENT = 0x0104
CMD_READ_DATA_READY = 0x0202
CMD_READ_MEASURED_VALUES = 0x0300
CMD_WAKEUP = 0x1103

MEASUREMENT_FIELDS = (
    "mc_1p0",
    "mc_2p5",
    "mc_4p0",
    "mc_10p0",
    "nc_0p5",
    "nc_1p0",
    "nc_2p5",
    "nc_4p0",
    "nc_10p0",
    "typical_particle_size",
)


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.monotonic() * 1000)


def _ticks_diff(now, then):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now, then)
    return now - then


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


def build_command(command, data_words=None):
    payload = bytearray(((command >> 8) & 0xFF, command & 0xFF))

    if data_words:
        for word in data_words:
            pair = bytes(((word >> 8) & 0xFF, word & 0xFF))
            payload.extend(pair)
            payload.append(calculate_crc(pair))

    return bytes(payload)


def parse_words(raw_data):
    if len(raw_data) % 3 != 0:
        raise ValueError("SPS30 frame must be a multiple of 3 bytes")

    words = []
    for index in range(0, len(raw_data), 3):
        pair = raw_data[index : index + 2]
        crc = raw_data[index + 2]
        if calculate_crc(pair) != crc:
            raise ValueError("CRC mismatch at word %d" % (index // 3))
        words.append((pair[0] << 8) | pair[1])

    return words


def unpack_float_words(words):
    if len(words) % 2 != 0:
        raise ValueError("Expected an even number of 16-bit words")

    floats = []
    for index in range(0, len(words), 2):
        payload = struct.pack(">HH", words[index], words[index + 1])
        floats.append(struct.unpack(">f", payload)[0])
    return floats


def parse_measurement(raw_data):
    words = parse_words(raw_data)
    values = unpack_float_words(words)
    if len(values) < len(MEASUREMENT_FIELDS):
        raise ValueError("Incomplete SPS30 measurement frame")

    return {
        field: values[index]
        for index, field in enumerate(MEASUREMENT_FIELDS)
    }


class SPS30Sensor:
    def __init__(self, i2c, address=SPS30_I2C_ADDRESS, timeout_s=30):
        self.i2c = i2c
        self.address = address
        self.timeout_s = int(timeout_s)
        self._started = False

    def probe(self):
        return self.address in self.i2c.scan()

    def _write_command(self, command, data_words=None):
        self.i2c.writeto(self.address, build_command(command, data_words))

    def wake_up(self):
        try:
            self._write_command(CMD_WAKEUP)
            _sleep_ms(50)
        except Exception:
            pass

    def start_measurement(self):
        self.wake_up()
        self._write_command(CMD_START_MEASUREMENT, [0x0300])
        _sleep_ms(1000)
        self._started = True

    def stop_measurement(self):
        try:
            self._write_command(CMD_STOP_MEASUREMENT)
        finally:
            self._started = False

    def _read_words(self, num_words):
        raw_data = self.i2c.readfrom(self.address, num_words * 3)
        return parse_words(raw_data)

    def data_ready(self):
        self._write_command(CMD_READ_DATA_READY)
        _sleep_ms(20)
        return self._read_words(1)[0] == 1

    def read_measurement(self, timeout_s=None):
        if not self._started:
            self.start_measurement()

        deadline_ms = int((timeout_s or self.timeout_s) * 1000)
        start_ms = _ticks_ms()
        while _ticks_diff(_ticks_ms(), start_ms) < deadline_ms:
            if self.data_ready():
                break
            _sleep_ms(500)
        else:
            self.stop_measurement()
            raise TimeoutError("SPS30 sensor did not become ready in time")

        self._write_command(CMD_READ_MEASURED_VALUES)
        _sleep_ms(50)
        raw_data = self.i2c.readfrom(self.address, 60)
        return parse_measurement(raw_data)
