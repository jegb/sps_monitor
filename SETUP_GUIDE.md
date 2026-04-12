# Setup & Deployment Guide

Automated setup script that handles installation, testing, and service deployment in one command.

---

## Quick Start (Recommended)

After cloning the repository, run:

```bash
cd sps_monitor
./setup.sh
```

This automatically:
1. ✅ Installs system & Python dependencies
2. ✅ Builds SPS30 driver
3. ✅ Validates hardware (scans I2C bus, tests each sensor)
4. ✅ Initializes SQLite database
5. ✅ Starts `sensor_reader` (data collection)
6. ✅ Starts `web_server` (dashboard at http://your-pi:5000)

**Complete in ~5-10 minutes** (depending on internet speed & hardware availability)

---

## What the Setup Script Does

### Phase 1: Prerequisites Check
- Verifies Python 3 installed
- Checks for Raspberry Pi
- Detects I2C bus
- Validates required system tools

### Phase 2: System Dependencies
Installs via `apt-get`:
- `python3-dev`, `python3-pip` - Python development
- `i2c-tools`, `libi2c-dev` - I2C support
- `build-essential` - Compiler tools
- `git` - Version control
- SSL/crypto libraries

### Phase 3: Python Dependencies
Installs via `pip3`:
- `paho-mqtt` - MQTT client
- `adafruit-circuitpython-*` - Sensor drivers
- `flask` - Web dashboard

### Phase 4: Build SPS30 Driver
- Compiles official Sensirion C driver
- Generates `libsps30.so`
- Enables I2C communication with SPS30

### Phase 5: Hardware Validation
Runs automated tests:
- **I2C Bus Scan** - Detects connected devices
- **SHT3x Test** - Temperature/humidity probe
- **SPS30 Test** - Particulate matter probe
- **DHT11 Test** - GPIO temperature/humidity probe (if used)

**Fails gracefully if sensors not connected** - allows testing in EMULATE mode.

### Phase 6: Database Setup
- Creates `sps30_data.db` SQLite database
- Initializes schema for sensor data

### Phase 7: Service Startup
Uses `systemd` user services (or background processes):
- **sps30-reader.service** - Collects sensor data every 60 sec
- **sps30-webserver.service** - Serves dashboard on port 5000

---

## Usage

### Full Automated Setup
```bash
./setup.sh
```

**Output:**
```
============================================================
CHECKING PREREQUISITES
============================================================
[✓] Python 3 found: 3.9.2
[✓] Git found
[✓] I2C detected

============================================================
INSTALLING SYSTEM DEPENDENCIES
============================================================
...

============================================================
RUNNING HARDWARE VALIDATION TESTS
============================================================
[✓] I2C bus scan completed
[✓] SHT3x test PASSED
[✓] SPS30 test PASSED
[✓] DHT11 test PASSED
[✓] At least one sensor validated. Proceeding with setup.

============================================================
SYSTEM STATUS
============================================================
✓ Setup Complete!

📊 Web Dashboard:
   http://192.168.1.100:5000

📋 Data Collection:
   ✓ Active

📝 Useful Commands:
   View sensor logs:    journalctl --user -u sps30-reader.service -f
   View webserver logs: journalctl --user -u sps30-webserver.service -f
```

### Test-Only Mode (No Installation)
```bash
./setup.sh --test-only
```
Runs hardware validation without installing or starting services.

### Skip Hardware Tests
```bash
./setup.sh --skip-tests
```
Installs & deploys without waiting for hardware tests (for testing with `EMULATE=True`).

### View System Status
```bash
./setup.sh --status
```
Shows current service status & dashboard URL.

---

## Accessing the Dashboard

Once setup completes, open your web browser:

```
http://<raspberry-pi-ip>:5000
```

Find your Pi's IP:
```bash
hostname -I
```

**Dashboard shows:**
- Live PM1.0, PM2.5, PM4.0, PM10 readings
- Real-time temperature & humidity
- Historical charts (1h, 6h, 24h, 7d, 30d)
- AQI quality indicators

---

## Service Management

### View Logs
```bash
# Sensor reader logs
journalctl --user -u sps30-reader.service -f

# Web server logs
journalctl --user -u sps30-webserver.service -f

# Combined
journalctl --user -u sps30-reader.service -u sps30-webserver.service -f
```

### Control Services
```bash
# Start services
systemctl --user start sps30-reader.service sps30-webserver.service

# Stop services
systemctl --user stop sps30-reader.service sps30-webserver.service

# Restart services
systemctl --user restart sps30-reader.service sps30-webserver.service

# Check status
systemctl --user status sps30-reader.service
systemctl --user status sps30-webserver.service

# Disable auto-start
systemctl --user disable sps30-reader.service sps30-webserver.service
```

---

## Configuration After Setup

### Change Sensor Type
Edit `config.py`:
```python
SENSOR_TYPE = "SHT3X"  # Options: "DHT11", "SHT31", "SHT3X"
EMULATE = False         # Set to True for testing without hardware
```

Then restart services:
```bash
systemctl --user restart sps30-reader.service
```

### Change Web Server Port
Edit `config.py` or modify service:
```bash
# View current service
cat ~/.config/systemd/user/sps30-webserver.service

# Edit service
systemctl --user edit sps30-webserver.service

# Change port in ExecStart, then restart:
systemctl --user daemon-reload
systemctl --user restart sps30-webserver.service
```

### Disable MQTT Publishing
Edit `config.py`:
```python
MQTT_BROKER = None  # Disable MQTT
```

---

## Troubleshooting Setup Failures

### "No sensors detected! Please check your hardware connections."

**Issue:** Hardware not connected or I2C not enabled.

**Solutions:**
1. Enable I2C on Raspberry Pi:
   ```bash
   sudo raspi-config
   # Interfacing Options → I2C → Yes
   ```

2. Verify wiring:
   - SDA → GPIO2 (Pin 3)
   - SCL → GPIO3 (Pin 5)
   - GND → Pin 6
   - Power → Correct voltage (3.3V or 5V)

3. Test I2C manually:
   ```bash
   sudo i2cdetect -y 1
   ```

4. Run setup again after fixing hardware.

### "Python 3 is not installed"

```bash
sudo apt-get install python3 python3-pip
```

### "SPS30 driver build failed"

```bash
cd c_sps30_i2c
# Follow instructions in RPI_DRIVER_BUILD.md
bash RPI_DRIVER_BUILD.md
cd ..
./setup.sh --skip-tests
```

### Services not starting

Check systemd logs:
```bash
journalctl --user -n 50  # Last 50 entries
systemctl --user status sps30-reader.service
systemctl --user status sps30-webserver.service
```

---

## Manual Setup (If Script Fails)

If you prefer manual installation:

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip i2c-tools build-essential

# 2. Install Python packages
pip3 install paho-mqtt adafruit-circuitpython-busio adafruit-circuitpython-sht31d flask

# 3. Build SPS30 driver
cd c_sps30_i2c
bash RPI_DRIVER_BUILD.md
cd ..

# 4. Test hardware
python3 test_sensors_unit.py --all

# 5. Initialize database
python3 init_sps30_db.py

# 6. Start services (background processes)
nohup python3 sensor_reader.py > sensor_reader.log 2>&1 &
nohup python3 web_server.py --port 5000 > web_server.log 2>&1 &

# 7. Access dashboard
# http://your-pi-ip:5000
```

---

## Data Storage

- **Database:** `sps30_data.db` (SQLite)
- **Logs:**
  - Systemd: `journalctl --user -u sps30-*`
  - Background: `sensor_reader.log`, `web_server.log`
- **Configuration:** `config.py`

---

## Post-Setup Validation

After setup completes:

```bash
# Check database has data
sqlite3 sps30_data.db "SELECT COUNT(*) FROM sps30_data;"

# Verify services running
systemctl --user status sps30-reader.service
systemctl --user status sps30-webserver.service

# Run comprehensive tests
python3 test_sensors_unit.py --all

# Check dashboard
# Open http://<pi-ip>:5000 in browser
# Should show live readings updating every ~30 sec
```

---

## Environment Variables (Optional)

For advanced configuration, set before running setup:

```bash
# Custom database location
export DB_PATH="/home/pi/sensor_data/sps30_data.db"

# Custom MQTT broker
export MQTT_BROKER="192.168.1.50"

# Run setup
./setup.sh
```

---

## Uninstalling

To remove services:

```bash
# Stop services
systemctl --user stop sps30-reader.service sps30-webserver.service

# Disable auto-start
systemctl --user disable sps30-reader.service sps30-webserver.service

# Remove service files
rm ~/.config/systemd/user/sps30-*.service
systemctl --user daemon-reload

# Optional: Keep data, remove Python packages
pip3 uninstall -y paho-mqtt adafruit-circuitpython-* flask
```

---

## Next Steps

After successful setup:

1. **Verify Data Collection**
   - Open dashboard: http://your-pi:5000
   - Check that readings update every 30 seconds
   - Wait 5-10 minutes for historical data

2. **Configure Systemd to Auto-Start (Optional)**
   ```bash
   systemctl --user enable sps30-reader.service sps30-webserver.service
   # Now services start automatically on reboot
   ```

3. **Set Up MQTT Integration (Optional)**
   - Edit `config.py` to configure broker
   - Connect Node-RED or other MQTT clients

4. **Monitor Logs Daily**
   ```bash
   journalctl --user -u sps30-reader.service --since today
   ```

---

## Support

For issues:

1. Check logs:
   ```bash
   journalctl --user -u sps30-reader.service -n 100
   ```

2. Run hardware tests:
   ```bash
   python3 test_sensors_unit.py --all
   ```

3. See TESTING.md for detailed troubleshooting

4. Check README.md for hardware wiring verification

---

**Status:** ✅ Automated setup complete
