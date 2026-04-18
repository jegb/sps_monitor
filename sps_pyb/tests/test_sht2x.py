import unittest

from sps_pyb.flash.lib.sensors.sht2x import calculate_crc, parse_humidity, parse_temperature


class SHT2XTests(unittest.TestCase):
    def test_crc_matches_known_frame(self):
        self.assertEqual(calculate_crc(bytes((0x68, 0x3A))), 0x7C)

    def test_parse_temperature(self):
        payload = bytes((0x68, 0x3A))
        frame = payload + bytes((calculate_crc(payload),))
        self.assertAlmostEqual(parse_temperature(frame), 24.6864, places=4)

    def test_parse_humidity(self):
        payload = bytes((0x5C, 0x24))
        frame = payload + bytes((calculate_crc(payload),))
        self.assertAlmostEqual(parse_humidity(frame), 38.9905, places=4)


if __name__ == "__main__":
    unittest.main()
