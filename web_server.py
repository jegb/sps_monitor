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
import shutil
from flask import Flask, jsonify, render_template, request
from db_metrics import ensure_schema, get_current_day_average, get_daily_averages, get_rolling_averages

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
    ensure_schema(db_path)
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


@app.route("/api/daily-averages")
def api_daily_averages():
    """Return materialized daily averages for the latest N days."""
    try:
        days = max(1, min(90, int(request.args.get("days", "10"))))
    except ValueError:
        days = 10
    return jsonify(get_daily_averages(DB_FILE, days=days))


@app.route("/api/summary")
def api_summary():
    """Return rolling 24h and latest daily aggregate summaries."""
    rolling_hours = request.args.get("hours", "24")
    try:
        hours = max(1, min(168, int(rolling_hours)))
    except ValueError:
        hours = 24

    return jsonify(
        {
            "rolling": get_rolling_averages(DB_FILE, hours=hours),
            "daily": get_current_day_average(DB_FILE),
        }
    )


@app.route("/api/system-status")
def api_system_status():
    """Return system status including disk usage."""
    try:
        # Get disk usage for root filesystem
        stat = shutil.disk_usage("/")

        total = stat.total / (1024 * 1024 * 1024)  # Convert to GB
        used = stat.used / (1024 * 1024 * 1024)
        free = stat.free / (1024 * 1024 * 1024)
        percent_used = (used / total) * 100 if total > 0 else 0

        # Get database file size in MB
        try:
            import os
            db_size = os.path.getsize(DB_FILE) / (1024 * 1024)
        except:
            db_size = 0

        return jsonify({
            "disk": {
                "total_gb": round(total, 2),
                "used_gb": round(used, 2),
                "free_gb": round(free, 2),
                "percent_used": round(percent_used, 1)
            },
            "database": {
                "size_mb": round(db_size, 2)
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPS30 Dashboard Server")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind address (127.0.0.1 for local only, 0.0.0.0 for all interfaces)")
    parser.add_argument("--db", type=str, default="sps30_data.db")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS with self-signed certificate")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    DB_FILE = args.db
    detect_schema(DB_FILE)  # validate on startup

    protocol = "https" if args.ssl else "http"
    port_display = 5443 if args.ssl else args.port
    print(f"🌫️  SPS30 Dashboard → {protocol}://{args.host}:{port_display}")

    # Setup HTTPS if requested
    ssl_context = None
    if args.ssl:
        import os
        cert_file = "cert.pem"
        key_file = "key.pem"
        if os.path.exists(cert_file) and os.path.exists(key_file):
            ssl_context = (cert_file, key_file)
            print(f"   Using SSL certificate: {cert_file}")
        else:
            print(f"   ⚠️  SSL requested but certificates not found at {cert_file}, {key_file}")
            print(f"   Run: openssl req -x509 -newkey rsa:2048 -nodes -out cert.pem -keyout key.pem -days 365")

    app.run(host=args.host, port=args.port, debug=args.debug, ssl_context=ssl_context)
