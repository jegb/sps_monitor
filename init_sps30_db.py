import argparse
from datetime import datetime, timedelta

from db_metrics import ensure_schema, refresh_daily_averages

DB_PATH = "sps30_data.db"

def init_db():
    ensure_schema(DB_PATH)
    print("✅ Database initialized (raw + daily aggregate tables).")

def rotate_data(retention_period):
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    now = datetime.now()
    if retention_period == "weekly":
        cutoff = now - timedelta(weeks=1)
    elif retention_period == "3months":
        cutoff = now - timedelta(days=90)
    elif retention_period == "6months":
        cutoff = now - timedelta(days=180)
    else:
        print("❌ Unsupported retention period. Use: weekly, 3months, or 6months.")
        return

    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("DELETE FROM sps30_data WHERE timestamp < ?", (cutoff_str,))
    conn.commit()
    conn.close()
    refresh_daily_averages(DB_PATH)
    print(f"🧹 Data older than {cutoff_str} has been deleted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or rotate SPS30 SQLite DB.")
    parser.add_argument("--rotate", choices=["weekly", "3months", "6months"], help="Data retention period")
    parser.add_argument(
        "--refresh-daily",
        action="store_true",
        help="Backfill the materialized daily averages table after initialization",
    )
    args = parser.parse_args()

    init_db()
    if args.refresh_daily:
        row_count = refresh_daily_averages(DB_PATH)
        print(f"📈 Refreshed {row_count} daily aggregate row(s).")

    if args.rotate:
        rotate_data(args.rotate)
