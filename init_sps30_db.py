import sqlite3
import argparse
from datetime import datetime, timedelta

DB_PATH = "sps30_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS sps30_data (
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        pm1 REAL,
        pm25 REAL,
        pm10 REAL,
        temp REAL,
        humidity REAL
    );
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized.")

def rotate_data(retention_period):
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
    print(f"🧹 Data older than {cutoff_str} has been deleted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or rotate SPS30 SQLite DB.")
    parser.add_argument("--rotate", choices=["weekly", "3months", "6months"], help="Data retention period")
    args = parser.parse_args()

    init_db()

    if args.rotate:
        rotate_data(args.rotate)
