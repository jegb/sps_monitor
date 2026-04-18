import unittest

from sps_pyb.flash.lib.app.runtime import PPD42CompatBuffer, PPD42SingleFieldMapper
from sps_pyb.flash.lib.sensors.ppd42 import (
    concentration_from_low_occupancy,
    estimate_mass_concentration_ugm3,
)


class PPD42Tests(unittest.TestCase):
    def test_concentration_from_low_occupancy(self):
        self.assertEqual(concentration_from_low_occupancy(3000000, 30), 100.0)

    def test_concentration_requires_positive_duration(self):
        with self.assertRaises(ValueError):
            concentration_from_low_occupancy(1000, 0)

    def test_estimate_mass_concentration_returns_positive_value(self):
        value = estimate_mass_concentration_ugm3(14.4054, particle_size_um=2.5)
        self.assertGreater(value, 0.0)

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

    def test_single_field_mapper_updates_pm25(self):
        mapper = PPD42SingleFieldMapper(
            "pm_2_5",
            particle_size_um=2.5,
            density_kg_m3=1650.0,
            calibration_factor=1.0,
        )

        snapshot, updated_field = mapper.update(14.4054)
        self.assertEqual(updated_field, "pm_2_5")
        self.assertIn("pm_2_5", snapshot)
        self.assertGreater(snapshot["pm_2_5"], 0.0)


if __name__ == "__main__":
    unittest.main()
