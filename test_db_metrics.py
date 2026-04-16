#!/usr/bin/env python3
"""Unit tests for station-side DB aggregate helpers."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db_metrics import (
    DAILY_TABLE,
    RAW_TABLE,
    build_mqtt_derived_metrics,
    ensure_schema,
    get_daily_averages,
    get_rolling_averages,
    refresh_daily_averages,
)


class DBMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        ensure_schema(str(self.db_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _insert_sample(
        self,
        timestamp: str,
        pm1: float,
        pm25: float,
        pm4: float,
        pm10: float,
        temp: float,
        humidity: float,
    ) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                f"""
                INSERT INTO {RAW_TABLE} (timestamp, pm1, pm25, pm4, pm10, temp, humidity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, pm1, pm25, pm4, pm10, temp, humidity),
            )
            conn.commit()
        finally:
            conn.close()

    def test_daily_averages_are_materialized(self) -> None:
        self._insert_sample("2026-04-15 00:15:00", 1.0, 10.0, 12.0, 20.0, 25.0, 55.0)
        self._insert_sample("2026-04-15 12:15:00", 3.0, 14.0, 16.0, 24.0, 27.0, 57.0)
        self._insert_sample("2026-04-16 09:00:00", 5.0, 20.0, 22.0, 30.0, 28.0, 60.0)

        refreshed = refresh_daily_averages(str(self.db_path))
        self.assertEqual(refreshed, 2)

        rows = get_daily_averages(str(self.db_path), days=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["day"], "2026-04-15")
        self.assertEqual(rows[0]["sample_count"], 2)
        self.assertAlmostEqual(rows[0]["pm25_avg"], 12.0)
        self.assertEqual(rows[1]["day"], "2026-04-16")
        self.assertEqual(rows[1]["sample_count"], 1)

    def test_rolling_averages_and_mqtt_metrics(self) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        within_24h = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        outside_24h = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")

        self._insert_sample(outside_24h, 1.0, 10.0, 12.0, 20.0, 25.0, 55.0)
        self._insert_sample(within_24h, 3.0, 14.0, 16.0, 24.0, 27.0, 57.0)

        refresh_daily_averages(str(self.db_path))
        rolling = get_rolling_averages(str(self.db_path), hours=24)
        self.assertEqual(rolling["sample_count"], 1)
        self.assertAlmostEqual(rolling["pm25_avg"], 14.0)

        derived = build_mqtt_derived_metrics(str(self.db_path))
        self.assertIn("rolling_24h_samples", derived)
        self.assertIn("pm_2_5_avg_24h", derived)
        self.assertIn("pm_2_5_day_avg", derived)

    def test_ensure_schema_creates_daily_table(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (DAILY_TABLE,),
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
