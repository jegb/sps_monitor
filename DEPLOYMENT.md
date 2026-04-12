# Deployment Architecture & Workflow

This document explains the deployment approach and why it's the right way.

---

## The Right Way: Layered Validation → Service Startup

### Why Not Just "Start Webserver"?

❌ **Wrong approach:**
```
Clone → Install → Start webserver
```

**Problems:**
- Webserver displays data from the database
- If `sensor_reader` isn't running, no data exists
- Dashboard shows "no data" error
- User confused about what's wrong

✅ **Right approach:**
```
Clone → Install → Test Hardware → Initialize DB → Start sensor_reader → Start webserver
```

**Benefits:**
- Hardware validated before services start
- Database initialized & ready
- `sensor_reader` populates data continuously
- `webserver` displays real live data
- Users see immediate results

---

## Deployment Architecture

### Component Relationship

```
Hardware (Sensors)
    ↓
test_sensors_unit.py (Validation)
    ↓
sensor_reader.py (Data Collection)
    ↓
sps30_data.db (SQLite Database)
    ↓
web_server.py (Dashboard)
    ↓
User Browser (http://pi:5000)
```

### Three-Tier Service Architecture

```
┌─────────────────────────────────────────────────┐
│  Tier 1: Web Interface (Port 5000)              │
│  web_server.py                                  │
│  - Serves HTTP dashboard                        │
│  - Queries database for readings                │
│  - Real-time updates via API                    │
└─────────────────────────────────────────────────┘
                    ↑
         (reads from database)
                    ↓
┌─────────────────────────────────────────────────┐
│  Tier 2: Data Storage (SQLite)                  │
│  sps30_data.db                                  │
│  - PM1.0, PM2.5, PM4.0, PM10                    │
│  - Temperature, Humidity                        │
│  - Timestamp of each reading                    │
└─────────────────────────────────────────────────┘
                    ↑
         (writes every 60 sec)
                    ↓
┌─────────────────────────────────────────────────┐
│  Tier 3: Sensor Data Collection (Background)    │
│  sensor_reader.py (as systemd service)          │
│  - Reads I2C/GPIO sensors                       │
│  - Stores to SQLite every 60 sec                │
│  - Publishes to MQTT (optional)                 │
│  - Runs continuously in background              │
└─────────────────────────────────────────────────┘
                    ↑
         (reads every 60 sec)
                    ↓
┌─────────────────────────────────────────────────┐
│  Tier 0: Hardware (Sensors)                     │
│  - SPS30 (PM via I2C @ 0x69)                    │
│  - SHT3x (Temp/Humidity via I2C @ 0x44)         │
│  - DHT11 (Temp/Humidity via GPIO4)              │
└─────────────────────────────────────────────────┘
```

---

## Why Each Step is Critical

### 1. Install Dependencies
- Without `adafruit-circuitpython-sht31d`, sensor reading fails
- Without `flask`, web server won't start
- Without `paho-mqtt`, MQTT publishing fails

### 2. Build SPS30 Driver
- SPS30 requires compiled C library (`libsps30.so`)
- Can't read SPS30 without this
- Takes ~2-3 minutes to build

### 3. Validate Hardware (`test_sensors_unit.py`)
- Proves sensors are connected & responding
- Identifies missing hardware early
- Prevents starting services with no data source
- **Critical:** If this fails, user sees the problem immediately

### 4. Initialize Database
- Creates SQLite schema
- Ensures database is writable
- Prevents "database locked" errors later

### 5. Start `sensor_reader.py`
- Must run continuously in background
- Collects data every 60 seconds
- Populates database with readings
- **Without this, webserver shows no data**

### 6. Start `web_server.py`
- Displays data from database (via Tier 2)
- Only useful after `sensor_reader` is running
- Serves dashboard at http://pi:5000

---

## Setup.sh Workflow

```
setup.sh (Main Entry Point)
├── check_prerequisites()
│   └── Verify Python 3, git, I2C enabled
├── install_system_dependencies()
│   └── sudo apt-get install python3-pip i2c-tools build-essential
├── install_python_dependencies()
│   └── pip3 install adafruit-circuitpython-* paho-mqtt flask
├── build_sps30_driver()
│   └── cd c_sps30_i2c && make
├── run_hardware_tests()
│   └── python3 test_sensors_unit.py --all
│       ├── Scan I2C bus
│       ├── Test SHT3x
│       ├── Test SPS30
│       └── Test DHT11
│   └── If ANY sensor passes → Continue
│   └── If NO sensors pass → ABORT with error
├── init_database()
│   └── python3 init_sps30_db.py
├── start_sensor_reader()
│   └── systemctl --user enable/start sps30-reader.service
├── start_web_server()
│   └── systemctl --user enable/start sps30-webserver.service
└── show_status()
    └── Display dashboard URL & useful commands
```

---

## Service Management with Systemd

### Why Systemd Services?

✅ **Advantages:**
- Auto-restart if process crashes
- Auto-start on Pi reboot
- Centralized logging (`journalctl`)
- Easy start/stop/status
- No manual process management

### User Services (No Root Required)

```bash
~/.config/systemd/user/sps30-reader.service
~/.config/systemd/user/sps30-webserver.service
```

**Starts automatically:**
- On system reboot
- If process crashes
- When user logs in (if `--user` services enabled)

---

## Failure Scenarios & Recovery

### Scenario 1: No Sensors Connected

**What happens:**
```
setup.sh → run_hardware_tests() → No sensors found → ERROR
```

**Output:**
```
✗ No sensors detected! Please check your hardware connections.
```

**User action:**
1. Check wiring
2. Enable I2C: `sudo raspi-config`
3. Run setup again: `./setup.sh`

**Why this is right:**
- User finds problem immediately, not after services start
- Prevents confusing "no data" dashboard errors

### Scenario 2: Only One Sensor Connected

**What happens:**
```
setup.sh → run_hardware_tests() → SHT3x detected → OK, continue
```

**Output:**
```
✓ At least one sensor validated. Proceeding with setup.
```

**Services start:**
- `sensor_reader.py` collects SHT3x data
- Dashboard displays temperature & humidity
- User can add more sensors later

### Scenario 3: Sensor Reader Crashes

**What happens:**
1. `sensor_reader.py` crashes
2. Systemd detects process died
3. Automatically restarts after 10 seconds
4. User checks logs if needed

**User action:**
```bash
# View logs
journalctl --user -u sps30-reader.service -f

# Restart manually if needed
systemctl --user restart sps30-reader.service
```

### Scenario 4: Database Gets Corrupted

**What happens:**
- `sensor_reader.py` fails to write
- Logs show database error
- Services automatically restart

**User action:**
```bash
# Backup old data
cp sps30_data.db sps30_data.db.backup

# Reinitialize
python3 init_sps30_db.py

# Restart services
systemctl --user restart sps30-reader.service
```

---

## Configuration Flexibility

### For Development/Testing

```bash
# Edit config.py
EMULATE = True          # Use fake sensor data
SENSOR_TYPE = "DHT11"   # Test with DHT11 only

# Run setup without tests
./setup.sh --skip-tests

# Or run with tests (will skip unavailable sensors)
./setup.sh --test-only
```

### For Production

```bash
# Edit config.py
EMULATE = False         # Use real sensors
SENSOR_TYPE = "SHT3X"   # Use actual hardware

# Full setup with validation
./setup.sh
```

### Custom Configuration

```bash
# Edit config.py
SENSOR_TYPE = "SHT3X"
DHT11_PIN = 17          # Non-standard GPIO
MQTT_BROKER = "192.168.1.50"
```

Then restart:
```bash
systemctl --user restart sps30-reader.service
```

---

## Data Flow During Operation

### Once Running (Every 60 seconds)

```
1. sensor_reader.py wakes up
2. Reads I2C/GPIO sensors
   - SHT3x: 0x44 (I2C)
   - SPS30: 0x69 (I2C)
   - DHT11: GPIO4 (if used)
3. Gets readings:
   - pm1, pm25, pm4, pm10 (from SPS30)
   - temp, humidity (from SHT3x or DHT11)
4. Stores to database:
   INSERT INTO sps30_data (timestamp, pm1, pm25, ..., temp, humidity)
   VALUES (now, <values>)
5. Publishes to MQTT (if enabled):
   airquality/sensor → {"pm_2_5": 5.67, "temp": 22.45, ...}
6. Goes back to sleep for 60 seconds
```

### Dashboard Access

```
User opens browser → http://pi:5000
↓
Flask web_server.py receives request
↓
Queries database:
  SELECT * FROM sps30_data WHERE timestamp > now - 1hour
↓
Renders JSON + HTML
↓
JavaScript on client:
  - Updates live values every 30 sec
  - Fetches historical data
  - Draws charts
↓
User sees:
  ✓ Real-time PM2.5, Temp, Humidity
  ✓ Historical charts
  ✓ AQI quality indicator
```

---

## Monitoring & Maintenance

### Daily Check

```bash
# View today's data collection
journalctl --user -u sps30-reader.service --since today

# Count how many readings collected
sqlite3 sps30_data.db "SELECT COUNT(*) FROM sps30_data WHERE DATE(timestamp) = DATE('now');"

# Check services are running
systemctl --user status sps30-reader.service sps30-webserver.service
```

### Weekly Maintenance

```bash
# Check logs for errors
journalctl --user -u sps30-reader.service --since 1 week

# Verify database size
ls -lh sps30_data.db

# Run hardware validation
python3 test_sensors_unit.py --all
```

### Monthly Cleanup

```bash
# Remove old data (optional)
sqlite3 sps30_data.db "DELETE FROM sps30_data WHERE timestamp < datetime('now', '-3 months');"

# Backup current data
cp sps30_data.db sps30_data.db.backup-$(date +%Y%m%d)
```

---

## Conclusion: Why This Approach is Right

✅ **Validates before deploying** - Catches hardware issues early
✅ **Proper service ordering** - Data collection before dashboard
✅ **Automated recovery** - Systemd restarts failed processes
✅ **Logging & diagnostics** - `journalctl` for troubleshooting
✅ **Configuration flexibility** - Easy to adjust after setup
✅ **Production-ready** - Auto-starts on reboot, handles failures
✅ **User experience** - Dashboard shows real data immediately

**One command deployment:**
```bash
./setup.sh
```

**Result:**
- ✓ All hardware validated
- ✓ All services running
- ✓ Dashboard ready at http://pi:5000
- ✓ Automatic monitoring & recovery active
- ✓ Data collection started

---

**This is the right way because it automates the entire production deployment workflow that would otherwise require manual steps, monitoring, and troubleshooting.**
