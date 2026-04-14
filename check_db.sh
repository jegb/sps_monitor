#!/bin/bash
# Database inspection utility for SPS30 monitor

DB_FILE="${1:-sps30_data.db}"

if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file '$DB_FILE' not found"
    exit 1
fi

echo "=========================================="
echo "SPS30 Database Inspector"
echo "=========================================="
echo "Database: $DB_FILE"
echo ""

echo "--- Schema ---"
sqlite3 "$DB_FILE" ".schema sps30_data"
echo ""

echo "--- Row Count ---"
sqlite3 "$DB_FILE" "SELECT COUNT(*) as total_rows FROM sps30_data;"
echo ""

echo "--- First 5 Records (Oldest) ---"
sqlite3 "$DB_FILE" -header -column "SELECT * FROM sps30_data ORDER BY timestamp ASC LIMIT 5;"
echo ""

echo "--- Last 5 Records (Newest) ---"
sqlite3 "$DB_FILE" -header -column "SELECT * FROM sps30_data ORDER BY timestamp DESC LIMIT 5;"
echo ""

echo "--- Data Range ---"
sqlite3 "$DB_FILE" -header -column "SELECT
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record,
    COUNT(*) as total_records
FROM sps30_data;"
echo ""

echo "--- Value Ranges ---"
sqlite3 "$DB_FILE" -header -column "SELECT
    MIN(pm1) as min_pm1, MAX(pm1) as max_pm1,
    MIN(pm25) as min_pm25, MAX(pm25) as max_pm25,
    MIN(pm10) as min_pm10, MAX(pm10) as max_pm10,
    MIN(temp) as min_temp, MAX(temp) as max_temp,
    MIN(humidity) as min_hum, MAX(humidity) as max_hum
FROM sps30_data;"
echo ""

# Optional: dump to CSV
if [ "$2" == "--export" ]; then
    OUTPUT="sps30_export_$(date +%Y%m%d_%H%M%S).csv"
    echo "Exporting to $OUTPUT..."
    sqlite3 "$DB_FILE" -header -csv "SELECT * FROM sps30_data ORDER BY timestamp ASC;" > "$OUTPUT"
    echo "Export complete: $OUTPUT"
fi
