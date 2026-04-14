# 🌫️ SPS30 Air Quality Monitor – Raspberry Pi Edition

This project uses the Sensirion SPS30 (I²C) with optional SHT3X family sensors (SHT30/31/35) or DHT11 to monitor PM1.0, PM2.5, PM4.0, PM10, temperature, and humidity. Data is logged to SQLite and published via MQTT to Node-RED for visualization.

**Supported Platforms:** Raspberry Pi Zero / Zero 2W / Pi 2 / Pi 3 / Pi 4 / Pi 5
**Architecture-independent:** Pure Python I2C driver works on all models (32-bit and 64-bit).

---

## 📦 Features

- **SPS30 readings via pure Python I²C driver** (architecture-independent, works on all RPi models)
- Modular sensor support for temperature and humidity (DHT11, SHT31, SHT3X family)
- SQLite database storage with rotation options
- **Web dashboard** with live + historical data visualization (Flask)
- MQTT publishing for Node-RED integration
- Optional systemd service for auto-start on boot
- CLI tool for testing I²C + sensor integration
- **No C compilation required** - pure Python implementation for SPS30

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

## 🔧 I²C Configuration & Pinout Reference

### RPI GPIO I2C Bus Specification

The Raspberry Pi (3/4/5) uses the **I²C-1** bus on fixed GPIO pins:
- **SDA (Data):** GPIO2 (Pin 3)
- **SCL (Clock):** GPIO3 (Pin 5)
- **GND:** Pins 6, 9, 14, 20, 25, 30, 34, 39
- **3.3V:** Pins 1, 17
- **5V:** Pins 2, 4

**Pull-up Resistors:**
- ✅ **Internal 1.8kΩ pull-ups enabled** on GPIO2 (SDA) and GPIO3 (SCL)
- ❌ **No external pull-up resistors required** for I²C lines
- The RPI I²C bus is pre-configured for standard mode (100 kHz) and fast mode (400 kHz)

### I²C Address Allocation & Collision Check

| Sensor | Address (hex) | Address (dec) | I²C Bus | Notes |
|--------|---------------|---------------|---------|-------|
| **SPS30** | **0x69** | **105** | I²C-1 | Particulate matter (PM1.0, PM2.5, PM4.0, PM10) |
| **SHT3X** (ADDR→GND) | 0x44 | 68 | I²C-1 | Temperature & Humidity (default config) |
| **SHT3X** (ADDR→VDD) | 0x45 | 69 | I²C-1 | Alternative address if two SHT3X sensors needed |
| **DHT11** | N/A (GPIO) | N/A | GPIO4 | Single-wire protocol, not I²C |

**Address Status:** ✅ **No collisions.** Each I²C device has a unique address on the bus.

### Voltage Rails & Power Domains

| Device | VDC Required | RPI Pin | Comments |
|--------|--------------|---------|----------|
| **SPS30** | 5.0V ± 5% | Pin 2 | **CRITICAL:** Must use 5V. Does not tolerate 3.3V. |
| **SHT3X** | 3.3V (nom.) | Pin 1 | Spec: 2.15V–5.5V, but 3.3V recommended for I²C compatibility. |
| **DHT11** | 3.3V–5.5V | Pin 1 or Pin 2 | Flexible. Use Pin 1 (3.3V) for safer margin. |
| **RPI Logic** | 3.3V | GPIO2, GPIO3 | SDA/SCL logic levels are 3.3V. |

**Important:** SPS30 I²C data lines (SDA/SCL) are internally 3.3V tolerant despite 5V power supply. No level shifter required.

### ⚠️ Voltage Domain Verification Checklist

Before powering the system:

- [ ] **SPS30:** VDD connected to **Pin 2 (5V)**, NOT Pin 1 (3.3V)
- [ ] **SHT3X:** VCC connected to **Pin 1 (3.3V)**
- [ ] **DHT11:** VCC connected to **Pin 1 (3.3V)** or **Pin 2 (5V)** (your choice)
- [ ] **GND:** All sensors share common ground on Pins 6, 9, 14, 20, 25, 30, 34, 39
- [ ] **I²C Lines:** SDA (GPIO2, Pin 3) and SCL (GPIO3, Pin 5) are 3.3V logic only
- [ ] **No external pullups** added to SDA/SCL (RPI internal pullups sufficient)

**Result:** If all items checked, I²C communication will be stable at 100–400 kHz.

---

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

> ⚠️ **CRITICAL:** DO NOT connect SPS30 VDD to Pin 1 (3.3V). Must use Pin 2 (5V).
> The SPS30 I²C data lines are 3.3V tolerant internally—no level shifter needed for logic signals.

---

### 🌡️ SHT31 (I²C Temp/Humidity Sensor) → Raspberry Pi

```
╔═════════════════════╦═══════════════════════════════════════════════════════╗
║ SHT31 Signal        ║ Raspberry Pi GPIO Pin & I²C Configuration              ║
╠═════════════════════╬═══════════════════════════════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V)                                          ║
║ GND                 ║ Pin 6 (GND)                                           ║
║ SDA                 ║ Pin 3 (GPIO2 / SDA) — Shared I²C Data Line            ║
║ SCL                 ║ Pin 5 (GPIO3 / SCL) — Shared I²C Clock Line           ║
║ ADDR                ║ Pin 6 (GND) → I²C Address: 0x44 (default)             ║
║ ADDR                ║ Pin 1 (3.3V) → I²C Address: 0x45 (alternative)        ║
╚═════════════════════╩═══════════════════════════════════════════════════════╝
```

**I²C Bus Configuration:** SHT31 communicates on the shared I²C-1 bus. No external pull-ups needed.

---

### 🌡️ DHT11 (Single-Wire GPIO Temp/Humidity Sensor) → Raspberry Pi

```
╔═════════════════════╦═══════════════════════════════════════════════════════╗
║ DHT11 Signal        ║ Raspberry Pi GPIO Pin & Notes                          ║
╠═════════════════════╬═══════════════════════════════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V) recommended, or Pin 2 (5V)                ║
║ DATA                ║ Pin 11 (GPIO17) — Single-wire protocol                 ║
║ GND                 ║ Pin 6 (GND) — Shared Ground                            ║
╚═════════════════════╩═══════════════════════════════════════════════════════╝
```

**Protocol:** DHT11 uses a proprietary single-wire protocol (not I²C).

**Pull-up Configuration:**
- ✅ If your DHT11 module has internal pull-up: No external resistor needed
- ⚠️ If module lacks pull-up: Add 10kΩ pull-up resistor between DATA (GPIO17) and VCC

**Note:** DHT11 is mutually exclusive with SHT3X sensors in the current config.py. Choose one temperature/humidity source.

---

### 🌡️ SHT3X Family (I²C Temp/Humidity Sensor) → Raspberry Pi

The SHT3X family includes **SHT30**, **SHT31**, and **SHT35** variants. All use the same I²C interface.

```
╔═════════════════════╦═════════════════════════════════════════════════════════╗
║ SHT3X Signal        ║ Raspberry Pi GPIO Pin & I²C Configuration                ║
╠═════════════════════╬═════════════════════════════════════════════════════════╣
║ VCC                 ║ Pin 1 (3.3V)                                            ║
║ GND                 ║ Pin 6 (GND) — Shared Ground                             ║
║ SDA                 ║ Pin 3 (GPIO2 / SDA) — Shared I²C Data Line              ║
║ SCL                 ║ Pin 5 (GPIO3 / SCL) — Shared I²C Clock Line             ║
║ ADDR                ║ Pin 6 (GND) → I²C Address 0x44 (default)                ║
║ ADDR                ║ Pin 1 (3.3V) → I²C Address 0x45 (alternative)           ║
╚═════════════════════╩═════════════════════════════════════════════════════════╝
```

**Specifications:**
- **Power:** 2.15V to 5.5V (3.3V recommended for stable I²C)
- **I²C Addresses:** 0x44 (ADDR→GND, default), 0x45 (ADDR→VDD, for second sensor)
- **Accuracy:** ±1.5% RH, ±0.1°C (SHT35) | ±2% RH, ±0.2°C (SHT30/31)
- **Response time:** <2 sec (temperature), <8 sec (humidity)
- **Bus:** Shared I²C-1 (GPIO2 SDA, GPIO3 SCL) with internal pull-ups

**Configuration in `config.py`:**
```python
SENSOR_TYPE = "SHT3X"  # or "SHT31" (backward compatible)
```

**Multiple SHT3X Support:** You can connect two SHT3X sensors on the same I²C bus by setting their ADDR pins differently (one to GND for 0x44, one to VDD for 0x45). However, the current codebase only reads from one sensor. Extend `sensors/sht31.py` to support address parameter if needed.

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

