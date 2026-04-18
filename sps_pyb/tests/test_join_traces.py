import unittest

from sps_pyb.tools.join_traces import build_topic_events, join_events


class JoinTracesTests(unittest.TestCase):
    def test_build_topic_events_decodes_raw_payload(self):
        records = [
            {
                "received_at": 1000.0,
                "mqtt_topic": "airquality/sensor_ppd42_raw",
                "raw_payload": (
                    '{"timestamp_utc":"2026-04-18T10:00:00Z",'
                    '"ppd42_particle_count":18.3,"temp":25.8,"humidity":47.6}'
                ),
            }
        ]

        events = build_topic_events(records, topic="airquality/sensor_ppd42_raw")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["ppd42_particle_count"], 18.3)
        self.assertEqual(events[0]["payload"]["temp"], 25.8)

    def test_join_events_pairs_nearest_reference(self):
        sample_events = [
            {
                "received_at": 1000.0,
                "payload": {
                    "timestamp_utc": "2015-01-01T00:03:22Z",
                    "ppd42_particle_count": 18.3633,
                    "temp": 25.8259,
                    "humidity": 47.6714,
                },
            }
        ]
        reference_events = [
            {
                "received_at": 1015.0,
                "payload": {
                    "pm_1_0": 1.9,
                    "pm_2_5": 6.5,
                    "pm_4_0": 10.2,
                    "pm_10_0": 12.0,
                },
            }
        ]

        rows = join_events(sample_events, reference_events, max_skew_s=45.0)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ppd42_particle_count"], 18.3633)
        self.assertEqual(rows[0]["pm_2_5"], 6.5)
        self.assertEqual(rows[0]["pair_age_s"], 15.0)


if __name__ == "__main__":
    unittest.main()
