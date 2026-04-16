#!/usr/bin/env python3
"""Upgrade an existing station database with daily aggregates and backfill them."""

from __future__ import annotations

import argparse

from db_metrics import ensure_schema, get_rolling_averages, refresh_daily_averages


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create/backfill station-side daily aggregate metrics.",
    )
    parser.add_argument("--db", default="sps30_data.db", help="SQLite database path")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Backfill only the most recent N days instead of the full dataset",
    )
    args = parser.parse_args()

    ensure_schema(args.db)
    row_count = refresh_daily_averages(args.db, days=args.days)
    rolling = get_rolling_averages(args.db, hours=24)

    print(f"✅ Schema ensured for {args.db}")
    if args.days is None:
        print(f"📈 Backfilled {row_count} daily aggregate row(s) across the full dataset.")
    else:
        print(f"📈 Refreshed {row_count} daily aggregate row(s) for the last {args.days} day(s).")
    print(
        "🕒 Rolling 24h snapshot: "
        f"samples={rolling['sample_count']}, "
        f"pm25_avg={rolling['pm25_avg']}, "
        f"pm10_avg={rolling['pm10_avg']}"
    )


if __name__ == "__main__":
    main()
