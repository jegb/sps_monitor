import unittest

from sps_pyb.flash.lib.sensors.aht10 import (
    is_busy,
    is_calibrated,
    parse_measurement_frame,
)


def build_frame(status, humidity_raw, temperature_raw):
    humidity_raw &= 0xFFFFF
    temperature_raw &= 0xFFFFF

    return bytes(
        (
            status & 0xFF,
            (humidity_raw >> 12) & 0xFF,
            (humidity_raw >> 4) & 0xFF,
            ((humidity_raw & 0x0F) << 4) | ((temperature_raw >> 16) & 0x0F),
            (temperature_raw >> 8) & 0xFF,
            temperature_raw & 0xFF,
        )
    )


class AHT10Tests(unittest.TestCase):
    def test_status_helpers(self):
        self.assertTrue(is_busy(0x80))
        self.assertFalse(is_busy(0x00))
        self.assertTrue(is_calibrated(0x08))
        self.assertFalse(is_calibrated(0x00))

    def test_parse_measurement_frame(self):
        frame = build_frame(0x08, 524288, 524288)
        parsed = parse_measurement_frame(frame)

        self.assertEqual(parsed["status"], 0x08)
        self.assertAlmostEqual(parsed["humidity"], 50.0, places=2)
        self.assertAlmostEqual(parsed["temperature"], 50.0, places=2)

    def test_parse_measurement_frame_requires_six_bytes(self):
        with self.assertRaises(ValueError):
            parse_measurement_frame(b"\x00")


if __name__ == "__main__":
    unittest.main()
