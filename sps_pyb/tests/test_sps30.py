import struct
import unittest

from sps_pyb.flash.lib.sensors.sps30 import calculate_crc, parse_measurement


def _encode_word(word):
    pair = bytes(((word >> 8) & 0xFF, word & 0xFF))
    return pair + bytes((calculate_crc(pair),))


def _encode_float(value):
    raw = struct.pack(">f", value)
    first_word = (raw[0] << 8) | raw[1]
    second_word = (raw[2] << 8) | raw[3]
    return _encode_word(first_word) + _encode_word(second_word)


class SPS30Tests(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(calculate_crc(b"\xBE\xEF"), 0x92)

    def test_parse_measurement_decodes_all_expected_fields(self):
        values = (
            1.0,
            2.5,
            4.0,
            10.0,
            11.0,
            12.0,
            13.0,
            14.0,
            15.0,
            0.5,
        )
        raw_data = b"".join(_encode_float(value) for value in values)

        measurement = parse_measurement(raw_data)

        self.assertAlmostEqual(measurement["mc_1p0"], 1.0)
        self.assertAlmostEqual(measurement["mc_2p5"], 2.5)
        self.assertAlmostEqual(measurement["mc_4p0"], 4.0)
        self.assertAlmostEqual(measurement["mc_10p0"], 10.0)
        self.assertAlmostEqual(measurement["nc_0p5"], 11.0)
        self.assertAlmostEqual(measurement["nc_10p0"], 15.0)
        self.assertAlmostEqual(measurement["typical_particle_size"], 0.5)


if __name__ == "__main__":
    unittest.main()
