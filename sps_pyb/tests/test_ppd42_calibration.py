import unittest

from sps_pyb.tools.ppd42_calibration import (
    fit_linear_model,
    fit_models,
    model_config_snippet,
    pair_payloads,
)


class PPD42CalibrationTests(unittest.TestCase):
    def test_pair_payloads_returns_row_when_timestamps_are_close(self):
        sample = {
            "timestamp_utc": "2026-04-18T12:00:00Z",
            "ppd42_particle_count": 10.5,
            "temp": 27.1,
            "humidity": 43.2,
        }
        reference = {
            "timestamp_utc": "2026-04-18T12:00:20Z",
            "pm_1_0": 1.0,
            "pm_2_5": 2.0,
            "pm_4_0": 3.0,
            "pm_10_0": 4.0,
        }

        row = pair_payloads(
            sample,
            reference,
            sample_received_at=1000.0,
            reference_received_at=1005.0,
            max_skew_s=30.0,
        )

        self.assertIsNotNone(row)
        self.assertEqual(row["ppd42_particle_count"], 10.5)
        self.assertEqual(row["pm_2_5"], 2.0)

    def test_pair_payloads_rejects_large_time_skew(self):
        row = pair_payloads(
            {"timestamp_utc": "2026-04-18T12:00:00Z", "ppd42_particle_count": 10.5},
            {"timestamp_utc": "2026-04-18T12:02:00Z", "pm_2_5": 2.0},
            sample_received_at=1744977600.0,
            reference_received_at=1744977720.0,
            max_skew_s=30.0,
        )
        self.assertIsNone(row)

    def test_pair_payloads_falls_back_to_receive_times_when_reference_has_no_timestamp(self):
        sample = {
            "timestamp_utc": "2015-01-01T00:03:22Z",
            "ppd42_particle_count": 18.3633,
            "temp": 25.8259,
            "humidity": 47.6714,
        }
        reference = {
            "pm_1_0": 1.9,
            "pm_2_5": 6.5,
            "pm_4_0": 10.2,
            "pm_10_0": 12.0,
        }

        row = pair_payloads(
            sample,
            reference,
            sample_received_at=1000.0,
            reference_received_at=1015.0,
            max_skew_s=45.0,
        )

        self.assertIsNotNone(row)
        self.assertEqual(row["ppd42_particle_count"], 18.3633)
        self.assertEqual(row["pm_2_5"], 6.5)
        self.assertEqual(row["pair_age_s"], 15.0)

    def test_pair_payloads_falls_back_to_receive_times_when_payload_clock_is_implausible(self):
        sample = {
            "timestamp_utc": "2015-01-01T00:03:22Z",
            "ppd42_particle_count": 18.3633,
        }
        reference = {
            "timestamp_utc": "2026-04-18T12:00:05Z",
            "pm_2_5": 6.5,
        }

        row = pair_payloads(
            sample,
            reference,
            sample_received_at=1000.0,
            reference_received_at=1002.0,
            max_skew_s=45.0,
        )

        self.assertIsNotNone(row)
        self.assertEqual(row["pair_age_s"], 2.0)

    def test_fit_linear_model_recovers_simple_line(self):
        model = fit_linear_model([(1.0, 3.0), (2.0, 5.0), (3.0, 7.0)])
        self.assertAlmostEqual(model["a"], 2.0)
        self.assertAlmostEqual(model["b"], 1.0)
        self.assertAlmostEqual(model["r2"], 1.0)

    def test_fit_models_builds_all_available_targets(self):
        rows = [
            {"ppd42_particle_count": 1.0, "pm_1_0": 2.0, "pm_2_5": 3.0},
            {"ppd42_particle_count": 2.0, "pm_1_0": 4.0, "pm_2_5": 5.0},
            {"ppd42_particle_count": 3.0, "pm_1_0": 6.0, "pm_2_5": 7.0},
        ]
        models = fit_models(rows, target_fields=("pm_1_0", "pm_2_5", "pm_4_0"))
        self.assertIn("pm_1_0", models)
        self.assertIn("pm_2_5", models)
        self.assertNotIn("pm_4_0", models)

    def test_model_config_snippet_contains_coefficients(self):
        snippet = model_config_snippet({
            "pm_2_5": {"a": 1.23, "b": 4.56, "r2": 0.99, "samples": 10},
        })
        self.assertIn("PPD42_LINEAR_PM_CALIBRATION", snippet)
        self.assertIn("'pm_2_5'", snippet)
        self.assertIn("1.23", snippet)


if __name__ == "__main__":
    unittest.main()
