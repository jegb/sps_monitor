import unittest

from pizerow.sensors.sht3x import calculate_crc, parse_measurement


def _encode_word(word):
    pair = bytes(((word >> 8) & 0xFF, word & 0xFF))
    return pair + bytes((calculate_crc(pair),))


class SHT3XTests(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(calculate_crc(b"\xBE\xEF"), 0x92)

    def test_parse_measurement_returns_temperature_and_humidity(self):
        raw_temp = int(round((25.0 + 45.0) * 65535.0 / 175.0))
        raw_humidity = int(round(50.0 * 65535.0 / 100.0))
        raw_data = _encode_word(raw_temp) + _encode_word(raw_humidity)

        temperature, humidity = parse_measurement(raw_data)

        self.assertAlmostEqual(temperature, 25.0, places=1)
        self.assertAlmostEqual(humidity, 50.0, places=1)


if __name__ == "__main__":
    unittest.main()
