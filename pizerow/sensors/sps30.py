import struct
import time

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    SMBus = None
    i2c_msg = None

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

    values = []
    for index in range(0, len(words), 2):
        payload = struct.pack(">HH", words[index], words[index + 1])
        values.append(struct.unpack(">f", payload)[0])
    return values


def parse_measurement(raw_data):
    words = parse_words(raw_data)
    floats = unpack_float_words(words)
    if len(floats) < len(MEASUREMENT_FIELDS):
        raise ValueError("Incomplete SPS30 measurement frame")
    return {field: floats[index] for index, field in enumerate(MEASUREMENT_FIELDS)}


class SPS30Sensor:
    def __init__(self, bus_num=1, address=SPS30_I2C_ADDRESS, timeout_s=30):
        self.bus_num = int(bus_num)
        self.address = int(address)
        self.timeout_s = int(timeout_s)

    def _ensure_smbus(self):
        if SMBus is None or i2c_msg is None:
            raise RuntimeError("smbus2 is not installed")

    def _write_command(self, bus, command, data_words=None):
        bus.i2c_rdwr(i2c_msg.write(self.address, build_command(command, data_words)))

    def _read_words(self, bus, num_words):
        read_msg = i2c_msg.read(self.address, num_words * 3)
        bus.i2c_rdwr(read_msg)
        return parse_words(bytes(read_msg))

    def probe(self):
        self._ensure_smbus()
        try:
            with SMBus(self.bus_num) as bus:
                self._write_command(bus, CMD_WAKEUP)
            return True
        except Exception:
            return False

    def stop_measurement(self):
        self._ensure_smbus()
        with SMBus(self.bus_num) as bus:
            self._write_command(bus, CMD_STOP_MEASUREMENT)

    def read_measurement(self, timeout_s=None):
        self._ensure_smbus()
        timeout = int(timeout_s or self.timeout_s)

        with SMBus(self.bus_num) as bus:
            try:
                self._write_command(bus, CMD_WAKEUP)
                time.sleep(0.05)
            except Exception:
                pass

            self._write_command(bus, CMD_START_MEASUREMENT, [0x0300])
            time.sleep(1.0)

            started = time.monotonic()
            while (time.monotonic() - started) < timeout:
                try:
                    self._write_command(bus, CMD_READ_DATA_READY)
                    time.sleep(0.02)
                    if self._read_words(bus, 1)[0] == 1:
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            else:
                self._write_command(bus, CMD_STOP_MEASUREMENT)
                raise TimeoutError("SPS30 sensor did not respond in time")

            self._write_command(bus, CMD_READ_MEASURED_VALUES)
            time.sleep(0.05)
            read_msg = i2c_msg.read(self.address, 60)
            bus.i2c_rdwr(read_msg)
            measurement = parse_measurement(bytes(read_msg))

            self._write_command(bus, CMD_STOP_MEASUREMENT)
            return measurement
