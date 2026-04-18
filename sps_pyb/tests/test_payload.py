import unittest

from sps_pyb.flash.lib.app.payload import PM_FIELDS, PAYLOAD_FIELDS, build_live_payload, build_sensor_record


class PayloadTests(unittest.TestCase):
    def test_build_live_payload_uses_exact_keys(self):
        record = build_sensor_record(
            "2026-04-17T12:00:00Z",
            {
                "mc_1p0": 1.24,
                "mc_2p5": 2.35,
                "mc_4p0": 3.46,
                "mc_10p0": 4.57,
            },
            25.14,
            59.64,
        )

        payload = build_live_payload(record)

        self.assertEqual(tuple(payload.keys()), PAYLOAD_FIELDS)
        self.assertEqual(payload["pm_1_0"], 1.24)
        self.assertEqual(payload["pm_2_5"], 2.35)
        self.assertEqual(payload["pm_4_0"], 3.46)
        self.assertEqual(payload["pm_10_0"], 4.57)
        self.assertEqual(payload["temp"], 25.14)
        self.assertEqual(payload["humidity"], 59.64)
        self.assertNotIn("ppd42_particle_count", payload)
        self.assertNotIn("ppd42_particle_size", payload)

    def test_build_sensor_record_allows_missing_pm_data(self):
        record = build_sensor_record(
            "2026-04-17T12:00:00Z",
            None,
            25.14,
            59.64,
        )

        self.assertIsNone(record["pm_1_0"])
        self.assertIsNone(record["pm_2_5"])
        self.assertIsNone(record["pm_4_0"])
        self.assertIsNone(record["pm_10_0"])
        self.assertEqual(record["temp"], 25.14)
        self.assertEqual(record["humidity"], 59.64)

    def test_build_live_payload_includes_ppd42_when_present(self):
        record = build_sensor_record(
            "2026-04-17T12:00:00Z",
            None,
            25.14,
            59.64,
            ppd42_particle_count=12.34567,
            ppd42_particle_size=2.5,
        )

        payload = build_live_payload(record)

        self.assertEqual(payload["ppd42_particle_count"], 12.3457)
        self.assertEqual(payload["ppd42_particle_size"], 2.5)

    def test_build_sensor_record_allows_pm_field_overrides(self):
        record = build_sensor_record(
            "2026-04-17T12:00:00Z",
            None,
            25.14,
            59.64,
            pm_fields={
                "pm_1_0": 11.11111,
                "pm_2_5": 22.22222,
                "pm_4_0": 33.33333,
                "pm_10_0": 44.44444,
            },
        )

        self.assertEqual(tuple(record[field_name] for field_name in PM_FIELDS), (11.1111, 22.2222, 33.3333, 44.4444))


if __name__ == "__main__":
    unittest.main()
