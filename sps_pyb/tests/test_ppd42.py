import unittest

from sps_pyb.flash.lib.app.runtime import PPD42CompatBuffer
from sps_pyb.flash.lib.sensors.ppd42 import concentration_from_low_occupancy


class PPD42Tests(unittest.TestCase):
    def test_concentration_from_low_occupancy(self):
        self.assertEqual(concentration_from_low_occupancy(3000000, 30), 100.0)

    def test_concentration_requires_positive_duration(self):
        with self.assertRaises(ValueError):
            concentration_from_low_occupancy(1000, 0)

    def test_compat_buffer_updates_fields_sequentially(self):
        compat = PPD42CompatBuffer()

        snapshot, updated_field = compat.update(10.0)
        self.assertEqual(updated_field, "pm_1_0")
        self.assertEqual(snapshot["pm_1_0"], 10.0)
        self.assertIsNone(snapshot["pm_2_5"])

        snapshot, updated_field = compat.update(20.0)
        self.assertEqual(updated_field, "pm_2_5")
        self.assertEqual(snapshot["pm_1_0"], 10.0)
        self.assertEqual(snapshot["pm_2_5"], 20.0)

        snapshot, updated_field = compat.update(30.0)
        self.assertEqual(updated_field, "pm_4_0")
        snapshot, updated_field = compat.update(40.0)
        self.assertEqual(updated_field, "pm_10_0")
        snapshot, updated_field = compat.update(50.0)
        self.assertEqual(updated_field, "pm_1_0")
        self.assertEqual(snapshot["pm_1_0"], 50.0)
        self.assertEqual(snapshot["pm_2_5"], 20.0)
        self.assertEqual(snapshot["pm_4_0"], 30.0)
        self.assertEqual(snapshot["pm_10_0"], 40.0)


if __name__ == "__main__":
    unittest.main()
