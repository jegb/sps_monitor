"""
SPS30 Air Quality Dashboard – Web Server
=========================================
Lightweight Flask server that reads from your existing SQLite DB
and serves a mobile-friendly dashboard with live + historical data.

Usage:
    python3 web_server.py                     # default: 0.0.0.0:5000
    python3 web_server.py --port 8080         # custom port
    python3 web_server.py --db /path/to/db    # custom DB path

Accessible from any device on the same network at http://<pi-ip>:5000
"""

import sqlite3
import json
import argparse
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# CONFIG – adjust DB_FILE to match your actual table/column names
# ---------------------------------------------------------------------------
DB_FILE = "sps30_data.db"

# Map your actual DB schema here.
# Both init_sps30_db.py and sensor_reader.py now use the same schema:
#   sps30_data(timestamp, pm1, pm25, pm4, pm10, temp, humidity)

TABLE = None
COLUMNS = None

SCHEMA_A = {
    "table": "sps30_data",
    "cols": {
        "ts": "timestamp",
        "pm1": "pm1",
        "pm25": "pm25",
        "pm4": "pm4",
        "pm10": "pm10",
        "temp": "temp",
        "humidity": "humidity",
    },
}


def detect_schema(db_path: str) -> dict:
    """Verify sps30_data table exists in the database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {r[0] for r in cur.fetchall()}
    conn.close()

    if SCHEMA_A["table"] in tables:
        return SCHEMA_A
    else:
        # Create the table if it doesn't exist
        print(f"⚠️  Table '{SCHEMA_A['table']}' not found. Creating it.")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sps30_data (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pm1 REAL, pm25 REAL, pm4 REAL, pm10 REAL,
                temp REAL, humidity REAL
            );
        """)
        conn.commit()
        conn.close()
        return SCHEMA_A


# ---------------------------------------------------------------------------
# FLASK APP
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder=".")


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/latest")
def api_latest():
    """Return the most recent sensor reading."""
    schema = detect_schema(DB_FILE)
    cols = schema["cols"]
    table = schema["table"]

    select_cols = [v for v in cols.values() if v is not None]
    sql = f"SELECT {', '.join(select_cols)} FROM {table} ORDER BY {cols['ts']} DESC LIMIT 1"

    conn = get_db()
    row = conn.execute(sql).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "no data"}), 404

    result = {}
    for key, col in cols.items():
        if col is not None:
            # Add 'Z' suffix to timestamp to indicate UTC
            if key == 'ts' and row[col]:
                result[key] = row[col] + 'Z'
            else:
                result[key] = row[col]
    return jsonify(result)


@app.route("/api/history")
def api_history():
    """
    Return historical readings.
    Query params:
        range  – 1h | 6h | 24h | 7d | 30d  (default: 24h)
    """
    range_param = request.args.get("range", "24h")
    range_map = {
        "1h": "-1 hour",
        "6h": "-6 hours",
        "24h": "-24 hours",
        "7d": "-7 days",
        "30d": "-30 days",
    }
    time_modifier = range_map.get(range_param, "-24 hours")

    schema = detect_schema(DB_FILE)
    cols = schema["cols"]
    table = schema["table"]

    select_cols = [v for v in cols.values() if v is not None]
    # Query using UTC time
    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM {table}
        WHERE {cols['ts']} >= datetime('now', '{time_modifier}')
        ORDER BY {cols['ts']} ASC
    """

    conn = get_db()
    rows = conn.execute(sql).fetchall()
    conn.close()

    data = []
    for row in rows:
        entry = {}
        for key, col in cols.items():
            if col is not None:
                # Add 'Z' suffix to timestamp to indicate UTC
                if key == 'ts' and row[col]:
                    entry[key] = row[col] + 'Z'
                else:
                    entry[key] = row[col]
        data.append(entry)

    return jsonify(data)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPS30 Dashboard Server")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--db", type=str, default="sps30_data.db")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    DB_FILE = args.db
    detect_schema(DB_FILE)  # validate on startup

    print(f"🌫️  SPS30 Dashboard → http://0.0.0.0:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=args.debug)
