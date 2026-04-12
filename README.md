# 🌫️ SPS30 Air Quality Monitor – Raspberry Pi Edition

This project uses the Sensirion SPS30 (I²C) with optional SHT3X family sensors (SHT30/31/35) or DHT11 to monitor PM1.0, PM2.5, PM4.0, PM10, temperature, and humidity. Data is logged to SQLite and published via MQTT to Node-RED for visualization.

---

## 📦 Features

- SPS30 readings via official C driver wrapped in Python (I²C)
- Modular sensor support for temperature and humidity (DHT11, SHT31, SHT3X family)
- SQLite database storage with rotation options
- **Web dashboard** with live + historical data visualization (Flask)
- MQTT publishing for Node-RED integration
- Optional systemd service for auto-start on boot
- CLI tool for testing I²C + sensor integration

---

## 🚀 Quick Start (Recommended)

After cloning the repository:

```bash
cd sps_monitor
./setup.sh
```

**That's it!** The setup script automatically:
1. ✅ Installs all dependencies (system & Python)
2. ✅ Builds SPS30 driver
3. ✅ Validates hardware (tests each sensor)
4. ✅ Initializes database
5. ✅ Starts sensor data collection (background)
6. ✅ Starts web dashboard

**Then open your browser:**
```
http://<raspberry-pi-ip>:5000
```

---

## Setup Details

### What setup.sh Does

```
Clone Repository
    ↓
./setup.sh (Single command)
    ├─ Installs system packages (build tools, I2C support)
    ├─ Installs Python libraries (sensor drivers, Flask, MQTT)
    ├─ Builds SPS30 C driver
    ├─ Validates hardware (I2C scan, sensor tests)
    ├─ Initializes SQLite database
    ├─ Starts sensor_reader.py (background data collection)
    ├─ Starts web_server.py (dashboard on port 5000)
    └─ Shows dashboard URL
```

### Manual Setup (Advanced)

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for:
- Step-by-step instructions
- Troubleshooting common issues
- Manual installation commands
- Service management

### Hardware Testing Only

To validate sensors without deploying services:

```bash
# Test only, no installation
./setup.sh --test-only

# Or run tests individually
python3 test_sensors_unit.py --scan          # I2C bus scan
python3 test_sensors_unit.py --sht3x         # Test SHT3x
python3 test_sensors_unit.py --sps30         # Test SPS30
python3 test_sensors_unit.py --dht11         # Test DHT11
python3 test_sensors_unit.py --all           # All tests
```

For complete testing reference, see [TESTING.md](TESTING.md).

---

## 📊 Running the Data Collection and Dashboard

### 1. Initialize the Database

```bash
python3 init_sps30_db.py
```

### 2. Start the Sensor Reader

```bash
python3 sensor_reader.py
```

This collects readings every 60 seconds and stores them in SQLite + publishes to MQTT.

### 3. Start the Web Dashboard

In another terminal:

```bash
python3 web_server.py                    # default: 0.0.0.0:5000
python3 web_server.py --port 8080        # custom port
python3 web_server.py --db /path/to/db   # custom DB path
python3 web_server.py --debug            # debug mode
```

Access the dashboard from any device on the network:
- **http://<pi-ip>:5000** (or your custom port)
- Shows live readings (PM1.0, PM2.5, PM4.0, PM10, Temp, Humidity)
- Historical charts with time range selector (1H, 6H, 24H, 7D, 30D)
- Real-time status indicator

---

## 🧩 Sensor Wiring Diagrams

(Refer to sections below for detailed connection guides.)


---

## 🔌 Wiring Diagrams

### 🧪 SPS30 → Raspberry Pi (I²C)

```
╔═════════════════════════════════════════════════════╗
║         SPS30 I²C Wiring to Raspberry Pi (3/4)      ║
╠══════════════╦════════════════════╦═════════════════╣
║ SPS30 Signal ║ Raspberry Pi Pin   ║ Notes           ║
╠══════════════╬════════════════════╬═════════════════╣
║ VDD          ║ Pin 2 (5V)         ║ 5V Power ONLY   ║
║ GND          ║ Pin 6 (GND)        ║ Shared Ground   ║
║ SDA          ║ Pin 3 (GPIO2 / SDA)║ I²C Data Line   ║
║ SCL          ║ Pin 5 (GPIO3 / SCL)║ I²C Clock Line  ║
║ SEL          ║ Pin 9 (GND)        ║ Force I²C Mode  ║
╚══════════════╩════════════════════╩═════════════════╝
```

> ⚠️ DO NOT connect SPS30 VDD to 3.3V. Sensor requires 5V power.

---

### 🌡️ SHT31 (I²C Temp/Humidity Sensor) → Raspberry Pi

```
╔═════════════════════╦═══════════════════════════════╗
║ SHT31 Signal        ║ Raspberry Pi GPIO Pin         ║
╠═════════════════════╬═══════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V)                  ║
║ GND                 ║ Pin 6 (GND)                   ║
║ SDA                 ║ Pin 3 (GPIO2 / SDA)           ║
║ SCL                 ║ Pin 5 (GPIO3 / SCL)           ║
╚═════════════════════╩═══════════════════════════════╝
```

---

### 🌡️ DHT11 (1-Wire GPIO Temp/Humidity Sensor) → Raspberry Pi

```
╔═════════════════════╦═══════════════════════════════╗
║ DHT11 Signal        ║ Raspberry Pi GPIO Pin         ║
╠═════════════════════╬═══════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V) or Pin 2 (5V)     ║
║ DATA                ║ Pin 11 (GPIO17)               ║
║ GND                 ║ Pin 6 (GND)                   ║
╚═════════════════════╩═══════════════════════════════╝
```

> ⚠️ Use a 10kΩ pull-up resistor between DATA and VCC if not included on the module.

---

### 🌡️ SHT3X Family (I²C Temp/Humidity Sensor) → Raspberry Pi

The SHT3X family includes **SHT30**, **SHT31**, and **SHT35** variants. All use the same I²C interface.

```
╔═════════════════════╦═══════════════════════════════╗
║ SHT3X Signal        ║ Raspberry Pi GPIO Pin         ║
╠═════════════════════╬═══════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V)                  ║
║ GND                 ║ Pin 6 (GND)                   ║
║ SDA                 ║ Pin 3 (GPIO2 / SDA)           ║
║ SCL                 ║ Pin 5 (GPIO3 / SCL)           ║
║ ADDR                ║ Pin 6 (GND) for 0x44 address  ║
║ ADDR                ║ Pin 2 (3.3V) for 0x45 address ║
╚═════════════════════╩═══════════════════════════════╝
```

**Specifications:**
- **Power:** 2.15V to 5.5V (3.3V recommended)
- **I²C Addresses:** 0x44 (default, ADDR→GND), 0x45 (ADDR→VDD)
- **Accuracy:** ±1.5% RH, ±0.1°C (SHT35) | ±2% RH, ±0.2°C (SHT30/31)
- **Response time:** <2 sec (temperature), <8 sec (humidity)

**Configuration in `config.py`:**
```python
SENSOR_TYPE = "SHT3X"  # or "SHT31" (backward compatible)
```

---


---

---

## 🧪 Testing & Validation

Pre-deployment sensor validation is critical. Use unit tests to probe each sensor individually before full system integration.

### Quick Sensor Validation

```bash
# Scan I2C bus for connected devices
python3 test_sensors_unit.py --scan

# Test individual sensors
python3 test_sensors_unit.py --sht3x       # SHT3x (I2C)
python3 test_sensors_unit.py --sps30       # SPS30 (I2C)
python3 test_sensors_unit.py --dht11       # DHT11 (GPIO)

# Comprehensive validation of all sensors
python3 test_sensors_unit.py --all
```

### Pre-Integration Checklist

1. ✓ Run `test_sensors_unit.py --scan` to verify I2C bus
2. ✓ Test each sensor individually with `--sht3x`, `--sps30`, `--dht11`
3. ✓ Run `test_sensors_unit.py --all` for full validation
4. ✓ All tests pass before starting `sensor_reader.py`

**Full documentation:** [TESTING.md](TESTING.md) | **Quick reference:** [TEST_QUICK_REFERENCE.md](TEST_QUICK_REFERENCE.md)

---

## ⚠️ Disclaimer

This project is provided for educational and prototyping purposes only.

> **Use at your own risk.**
> The authors and contributors assume no responsibility or liability for damage to hardware, health, or environment resulting from the use or misuse of this software and wiring setup. Always double-check voltage levels, connections, and sensor datasheets before powering your circuit.

