#!/bin/bash
# Reset/clean SPS30 database

DB_FILE="${1:-sps30_data.db}"

echo "=========================================="
echo "SPS30 Database Reset Utility"
echo "=========================================="

if [ ! -f "$DB_FILE" ]; then
    echo "Database '$DB_FILE' does not exist."
    echo "Creating new database..."
    python3 init_sps30_db.py
    exit 0
fi

echo "Current database: $DB_FILE"
sqlite3 "$DB_FILE" "SELECT COUNT(*) as current_rows FROM sps30_data;"

echo ""
echo "WARNING: This will delete all data in the database!"
read -p "Are you sure you want to reset the database? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

# Backup existing database
BACKUP="sps30_data_backup_$(date +%Y%m%d_%H%M%S).db"
echo "Creating backup: $BACKUP"
cp "$DB_FILE" "$BACKUP"

# Delete existing database
echo "Removing old database..."
rm "$DB_FILE"

# Recreate fresh database
echo "Creating new database..."
python3 init_sps30_db.py

echo ""
echo "Database reset complete!"
echo "Backup saved as: $BACKUP"
