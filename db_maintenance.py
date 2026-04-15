#!/usr/bin/env python3
"""
Database maintenance script - removes old records and reclaims disk space.
Designed to run via cron for automated housekeeping.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import os

DB_FILE = "sps30_data.db"
RETENTION_DAYS = 90  # Keep 3 months of data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_db_size():
    """Get database file size in MB."""
    if os.path.exists(DB_FILE):
        size_bytes = os.path.getsize(DB_FILE)
        return size_bytes / (1024 * 1024)
    return 0

def maintain_db():
    """Delete old records and reclaim disk space."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # Get initial stats
        c.execute("SELECT COUNT(*) FROM sps30_data")
        initial_count = c.fetchone()[0]
        size_before = get_db_size()

        # Delete old records
        cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("DELETE FROM sps30_data WHERE timestamp < ?", (cutoff,))
        deleted_count = c.rowcount

        # Reclaim disk space
        c.execute("VACUUM")
        conn.commit()

        # Get final stats
        c.execute("SELECT COUNT(*) FROM sps30_data")
        final_count = c.fetchone()[0]
        size_after = get_db_size()

        conn.close()

        # Log results
        logging.info(f"Retention policy: {RETENTION_DAYS} days")
        logging.info(f"Deleted records: {deleted_count} (from {initial_count} to {final_count})")
        logging.info(f"DB file size: {size_before:.2f} MB → {size_after:.2f} MB")
        logging.info(f"Space recovered: {size_before - size_after:.2f} MB")

    except Exception as e:
        logging.error(f"Database maintenance failed: {e}")

if __name__ == "__main__":
    maintain_db()
