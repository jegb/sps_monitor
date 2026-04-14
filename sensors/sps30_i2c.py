"""
Pure Python SPS30 I2C driver using smbus2.
Compatible with all Raspberry Pi models.
"""
import time
import struct
from smbus2 import SMBus

SPS30_I2C_ADDRESS = 0x69

# Commands
CMD_START_MEASUREMENT = 0x0010
CMD_STOP_MEASUREMENT = 0x0104
CMD_READ_DATA_READY = 0x0202
CMD_READ_MEASURED_VALUES = 0x0300
CMD_SLEEP = 0x1001
CMD_WAKEUP = 0x1103
CMD_RESET = 0xD304


class SPS30Measurement:
    """SPS30 measurement data structure."""
    def __init__(self):
        self.mc_1p0 = 0.0
        self.mc_2p5 = 0.0
        self.mc_4p0 = 0.0
        self.mc_10p0 = 0.0
        self.nc_0p5 = 0.0
        self.nc_1p0 = 0.0
        self.nc_2p5 = 0.0
        self.nc_4p0 = 0.0
        self.nc_10p0 = 0.0
        self.typical_particle_size = 0.0


def _calculate_crc(data):
    """Calculate CRC-8 checksum for SPS30."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
    return crc & 0xFF


def _write_command(bus, address, command, data=None):
    """Write command to SPS30."""
    cmd_bytes = [(command >> 8) & 0xFF, command & 0xFF]

    if data is not None:
        for word in data:
            cmd_bytes.append((word >> 8) & 0xFF)
            cmd_bytes.append(word & 0xFF)
            cmd_bytes.append(_calculate_crc([(word >> 8) & 0xFF, word & 0xFF]))

    bus.write_i2c_block_data(address, cmd_bytes[0], cmd_bytes[1:])


def _read_words(bus, address, num_words):
    """Read words with CRC from SPS30."""
    # Each word is 2 bytes + 1 CRC byte
    num_bytes = num_words * 3
    raw_data = bus.read_i2c_block_data(address, 0x00, num_bytes)

    words = []
    for i in range(0, len(raw_data), 3):
        word_bytes = raw_data[i:i+2]
        crc = raw_data[i+2]

        if _calculate_crc(word_bytes) != crc:
            raise ValueError(f"CRC mismatch for word at position {i}")

        word = (word_bytes[0] << 8) | word_bytes[1]
        words.append(word)

    return words


def read_sps30(bus_num=1, timeout=30, debug=False):
    """
    Read measurement from SPS30 sensor.

    Args:
        bus_num: I2C bus number (default: 1)
        timeout: Maximum seconds to wait for data ready (default: 30)
        debug: Print debug messages (default: False)

    Returns:
        SPS30Measurement object

    Raises:
        TimeoutError: If sensor doesn't respond within timeout
    """
    with SMBus(bus_num) as bus:
        # Try waking up the sensor first
        try:
            if debug:
                print("Waking up sensor...")
            _write_command(bus, SPS30_I2C_ADDRESS, CMD_WAKEUP)
            time.sleep(0.05)
        except Exception as e:
            if debug:
                print(f"Wakeup error (may be OK): {e}")

        # Start measurement
        if debug:
            print("Starting measurement...")
        _write_command(bus, SPS30_I2C_ADDRESS, CMD_START_MEASUREMENT, [0x0300])
        time.sleep(1)  # Wait for sensor to stabilize

        # Wait for data ready
        if debug:
            print("Waiting for data ready...")
        start_time = time.time()
        attempts = 0
        while (time.time() - start_time) < timeout:
            try:
                attempts += 1
                _write_command(bus, SPS30_I2C_ADDRESS, CMD_READ_DATA_READY)
                time.sleep(0.02)
                words = _read_words(bus, SPS30_I2C_ADDRESS, 1)
                if debug and attempts % 5 == 0:
                    print(f"Attempt {attempts}: data_ready = {words[0]}")
                if words[0] == 1:  # Data ready
                    if debug:
                        print("Data ready!")
                    break
            except Exception as e:
                if debug and attempts % 10 == 0:
                    print(f"Read error: {e}")
            time.sleep(0.5)
        else:
            _write_command(bus, SPS30_I2C_ADDRESS, CMD_STOP_MEASUREMENT)
            raise TimeoutError(f"SPS30 sensor did not respond within {timeout} seconds (attempted {attempts} times)")

        # Read measurement data (10 float values = 20 words)
        _write_command(bus, SPS30_I2C_ADDRESS, CMD_READ_MEASURED_VALUES)
        time.sleep(0.05)
        words = _read_words(bus, SPS30_I2C_ADDRESS, 20)

        # Stop measurement
        _write_command(bus, SPS30_I2C_ADDRESS, CMD_STOP_MEASUREMENT)

        # Parse measurement data
        measurement = SPS30Measurement()
        floats = []
        for i in range(0, len(words), 2):
            bytes_data = struct.pack('>HH', words[i], words[i+1])
            value = struct.unpack('>f', bytes_data)[0]
            floats.append(value)

        measurement.mc_1p0 = floats[0]
        measurement.mc_2p5 = floats[1]
        measurement.mc_4p0 = floats[2]
        measurement.mc_10p0 = floats[3]
        measurement.nc_0p5 = floats[4]
        measurement.nc_1p0 = floats[5]
        measurement.nc_2p5 = floats[6]
        measurement.nc_4p0 = floats[7]
        measurement.nc_10p0 = floats[8]
        measurement.typical_particle_size = floats[9]

        return measurement
