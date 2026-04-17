import unittest

from pizerow.app.payload import PAYLOAD_FIELDS, build_live_payload, build_sensor_record


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
        self.assertEqual(payload["pm_1_0"], 1.2)
        self.assertEqual(payload["pm_2_5"], 2.4)
        self.assertEqual(payload["pm_4_0"], 3.5)
        self.assertEqual(payload["pm_10_0"], 4.6)
        self.assertEqual(payload["temp"], 25.1)
        self.assertEqual(payload["humidity"], 59.6)


if __name__ == "__main__":
    unittest.main()
