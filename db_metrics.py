#!/usr/bin/env python3
"""Shared SQLite schema and aggregate helpers for SPS30 station data."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

RAW_TABLE = "sps30_data"
DAILY_TABLE = "sps30_daily_averages"

RAW_COLUMNS: dict[str, str] = {
    "timestamp": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    "pm1": "REAL",
    "pm25": "REAL",
    "pm4": "REAL",
    "pm10": "REAL",
    "temp": "REAL",
    "humidity": "REAL",
    "particle_count": "REAL",
    "particle_size": "REAL",
}

DAILY_COLUMNS: tuple[str, ...] = (
    "day",
    "sample_count",
    "pm1_avg",
    "pm25_avg",
    "pm4_avg",
    "pm10_avg",
    "temp_avg",
    "humidity_avg",
    "particle_count_avg",
    "particle_size_avg",
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _existing_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def ensure_schema(db_path: str) -> None:
    """Create or upgrade the raw and aggregate tables."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {RAW_TABLE} (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pm1 REAL,
                pm25 REAL,
                pm4 REAL,
                pm10 REAL,
                temp REAL,
                humidity REAL,
                particle_count REAL,
                particle_size REAL
            );
            """
        )

        existing = _existing_columns(conn, RAW_TABLE)
        for column_name, column_type in RAW_COLUMNS.items():
            if column_name not in existing:
                conn.execute(
                    f"ALTER TABLE {RAW_TABLE} ADD COLUMN {column_name} {column_type};"
                )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DAILY_TABLE} (
                day TEXT PRIMARY KEY,
                sample_count INTEGER NOT NULL,
                pm1_avg REAL,
                pm25_avg REAL,
                pm4_avg REAL,
                pm10_avg REAL,
                temp_avg REAL,
                humidity_avg REAL,
                particle_count_avg REAL,
                particle_size_avg REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{RAW_TABLE}_timestamp ON {RAW_TABLE}(timestamp);"
        )
        conn.commit()
    finally:
        conn.close()


def _day_cutoff(days: int) -> tuple[str, str]:
    lookback_days = max(0, int(days) - 1)
    modifier = f"-{lookback_days} days"
    return modifier, modifier


def refresh_daily_averages(db_path: str, days: int | None = None) -> int:
    """Backfill or refresh materialized daily averages from raw readings."""
    ensure_schema(db_path)
    conn = _connect(db_path)
    try:
        params: tuple[Any, ...] = ()
        where_sql = ""
        if days is not None:
            modifier, _ = _day_cutoff(days)
            cutoff_day = conn.execute("SELECT date('now', ?)", (modifier,)).fetchone()[0]
            conn.execute(f"DELETE FROM {DAILY_TABLE} WHERE day >= ?", (cutoff_day,))
            where_sql = "WHERE date(timestamp) >= date('now', ?)"
            params = (modifier,)
        else:
            conn.execute(f"DELETE FROM {DAILY_TABLE}")

        rows = conn.execute(
            f"""
            SELECT
                date(timestamp) AS day,
                COUNT(*) AS sample_count,
                AVG(pm1) AS pm1_avg,
                AVG(pm25) AS pm25_avg,
                AVG(pm4) AS pm4_avg,
                AVG(pm10) AS pm10_avg,
                AVG(temp) AS temp_avg,
                AVG(humidity) AS humidity_avg,
                AVG(particle_count) AS particle_count_avg,
                AVG(particle_size) AS particle_size_avg
            FROM {RAW_TABLE}
            {where_sql}
            GROUP BY date(timestamp)
            ORDER BY day ASC
            """,
            params,
        ).fetchall()

        conn.executemany(
            f"""
            INSERT INTO {DAILY_TABLE} (
                day,
                sample_count,
                pm1_avg,
                pm25_avg,
                pm4_avg,
                pm10_avg,
                temp_avg,
                humidity_avg,
                particle_count_avg,
                particle_size_avg,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            [
                (
                    row["day"],
                    row["sample_count"],
                    row["pm1_avg"],
                    row["pm25_avg"],
                    row["pm4_avg"],
                    row["pm10_avg"],
                    row["temp_avg"],
                    row["humidity_avg"],
                    row["particle_count_avg"],
                    row["particle_size_avg"],
                )
                for row in rows
            ],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def get_rolling_averages(db_path: str, hours: int = 24) -> dict[str, Any]:
    """Return rolling averages over the requested hour window."""
    ensure_schema(db_path)
    modifier = f"-{max(1, int(hours))} hours"
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS sample_count,
                AVG(pm1) AS pm1_avg,
                AVG(pm25) AS pm25_avg,
                AVG(pm4) AS pm4_avg,
                AVG(pm10) AS pm10_avg,
                AVG(temp) AS temp_avg,
                AVG(humidity) AS humidity_avg
            FROM {RAW_TABLE}
            WHERE timestamp >= datetime('now', ?)
            """,
            (modifier,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "window_hours": max(1, int(hours)),
        "sample_count": int(row["sample_count"] or 0),
        "pm1_avg": row["pm1_avg"],
        "pm25_avg": row["pm25_avg"],
        "pm4_avg": row["pm4_avg"],
        "pm10_avg": row["pm10_avg"],
        "temp_avg": row["temp_avg"],
        "humidity_avg": row["humidity_avg"],
    }


def get_current_day_average(db_path: str) -> dict[str, Any] | None:
    """Return today's materialized daily averages, or the latest available day."""
    ensure_schema(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f"SELECT * FROM {DAILY_TABLE} WHERE day = date('now') LIMIT 1"
        ).fetchone()
        if row is None:
            row = conn.execute(
                f"SELECT * FROM {DAILY_TABLE} ORDER BY day DESC LIMIT 1"
            ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def get_daily_averages(db_path: str, days: int = 10) -> list[dict[str, Any]]:
    """Return the latest N daily aggregate rows in chronological order."""
    ensure_schema(db_path)
    refresh_daily_averages(db_path, days=days)
    modifier, _ = _day_cutoff(days)
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"""
            SELECT {", ".join(DAILY_COLUMNS)}, updated_at
            FROM {DAILY_TABLE}
            WHERE day >= date('now', ?)
            ORDER BY day ASC
            """,
            (modifier,),
        ).fetchall()
    finally:
        conn.close()

    return [{key: row[key] for key in row.keys()} for row in rows]


def build_mqtt_derived_metrics(db_path: str) -> dict[str, Any]:
    """Return derived average fields for station-side MQTT publishing."""
    rolling = get_rolling_averages(db_path, hours=24)
    today = get_current_day_average(db_path)

    derived: dict[str, Any] = {
        "rolling_24h_samples": rolling["sample_count"],
    }
    rolling_fields = (
        ("pm1_avg", "pm_1_0_avg_24h"),
        ("pm25_avg", "pm_2_5_avg_24h"),
        ("pm4_avg", "pm_4_0_avg_24h"),
        ("pm10_avg", "pm_10_0_avg_24h"),
        ("temp_avg", "temp_avg_24h"),
        ("humidity_avg", "humidity_avg_24h"),
    )
    for source_key, target_key in rolling_fields:
        value = rolling.get(source_key)
        if value is not None:
            derived[target_key] = round(float(value), 3)

    if today is not None:
        derived["day_samples"] = int(today["sample_count"])
        derived["day"] = today["day"]
        daily_fields = (
            ("pm1_avg", "pm_1_0_day_avg"),
            ("pm25_avg", "pm_2_5_day_avg"),
            ("pm4_avg", "pm_4_0_day_avg"),
            ("pm10_avg", "pm_10_0_day_avg"),
            ("temp_avg", "temp_day_avg"),
            ("humidity_avg", "humidity_day_avg"),
        )
        for source_key, target_key in daily_fields:
            value = today.get(source_key)
            if value is not None:
                derived[target_key] = round(float(value), 3)

    return derived
