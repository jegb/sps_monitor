import unittest

from sps_pyb.flash.mock_publish import build_mock_payload


class MockPublishTests(unittest.TestCase):
    def test_build_mock_payload_uses_expected_keys(self):
        payload = build_mock_payload(0)

        self.assertEqual(
            tuple(payload.keys()),
            ("pm_1_0", "pm_2_5", "pm_4_0", "pm_10_0", "temp", "humidity"),
        )

    def test_build_mock_payload_changes_with_sequence(self):
        first = build_mock_payload(0)
        second = build_mock_payload(1)

        self.assertNotEqual(first, second)
        self.assertEqual(first["pm_1_0"], 1.0)
        self.assertEqual(second["pm_1_0"], 1.2)
        self.assertEqual(first["temp"], 24.0)
        self.assertEqual(second["humidity"], 46.3)


if __name__ == "__main__":
    unittest.main()
