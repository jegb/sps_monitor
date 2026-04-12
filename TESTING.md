# Sensor Testing & Validation Guide

This guide covers pre-deployment sensor validation using unit tests for individual hardware probing.

## Quick Start

### Scan I2C Bus for Connected Devices
```bash
python3 test_sensors_unit.py --scan
```

Output identifies all I2C devices by address:
```
Address      Hex      Device
-----------------------------------------------------
0x44         0x44     SHT3X (default addr, ADDR→GND)
0x69         0x69     SPS30
```

---

## Individual Sensor Testing

### SHT3x Sensor (Temperature/Humidity)
Test the SHT3x family (SHT30, SHT31, SHT35) on I2C.

**Default address (ADDR pin connected to GND):**
```bash
python3 test_sensors_unit.py --sht3x
```

**Alternate address (ADDR pin connected to 3.3V):**
```bash
python3 test_sensors_unit.py --sht3x --addr 0x45
```

**Multiple iterations:**
```bash
python3 test_sensors_unit.py --sht3x --iterations 5
```

**Expected output:**
```
============================================================
SHT3X SENSOR TEST (I2C Address: 0x44)
============================================================
Connecting to SHT3x at 0x44...
Attempt     Temp (°C)       Humidity (%RH)       Status
----------------------------------------------------------------------
1           22.45           45.32                ✓ OK
2           22.47           45.28                ✓ OK
3           22.46           45.31                ✓ OK

✓ SHT3x test PASSED
```

---

### SPS30 Sensor (Particulate Matter)
Test the SPS30 on I2C at address 0x69.

```bash
python3 test_sensors_unit.py --sps30
```

**With multiple iterations:**
```bash
python3 test_sensors_unit.py --sps30 --iterations 2
```

**Expected output:**
```
============================================================
SPS30 SENSOR TEST (I2C Address: 0x69)
============================================================
Starting SPS30 measurement sequence...
(SPS30 requires 8+ seconds for data to stabilize)

Attempt     PM1.0        PM2.5        PM4.0        PM10.0       Status
--------------------------------------------------------------------------------
1           2.34         5.67         8.90         12.34        ✓ OK
2           2.35         5.68         8.91         12.35        ✓ OK

✓ SPS30 test PASSED
```

**⚠️ Note:** SPS30 requires ~8-10 seconds between reads for data stabilization. Tests automatically wait.

---

### DHT11 Sensor (GPIO-based Temperature/Humidity)
Test DHT11 on GPIO pin.

**Default GPIO pin (4):**
```bash
python3 test_sensors_unit.py --dht11
```

**Specific GPIO pin:**
```bash
python3 test_sensors_unit.py --dht11 --pin 17
```

**Expected output:**
```
============================================================
DHT11 SENSOR TEST (GPIO Pin: 4)
============================================================
Connecting to DHT11 on GPIO4...
Attempt     Temp (°C)       Humidity (%RH)       Status
----------------------------------------------------------------------
1           23.0            46.0                 ✓ OK
2           23.0            46.0                 ✓ OK
3           23.0            46.0                 ✓ OK

✓ DHT11 test PASSED
```

**⚠️ Note:** DHT11 has 2-second minimum read interval. Tests automatically wait between iterations.

---

## Comprehensive Testing

### Test All Sensors
Run full validation suite on all connected sensors:
```bash
python3 test_sensors_unit.py --all
```

**Output:**
```
============================================================
COMPREHENSIVE SENSOR TEST SUITE
============================================================

[I2C bus scan results...]
[SHT3x test results...]
[SPS30 test results...]
[DHT11 test results...]

============================================================
TEST SUMMARY
============================================================
Test                      Result
----------------------------------------
I2C Bus Scan              PASSED
SHT3x Sensor              PASSED
SPS30 Sensor              PASSED
DHT11 Sensor              PASSED
```

---

## Test Configuration

All tests read from `config.py`:
- `SENSOR_TYPE`: Used to determine which sensor to test
- `DHT11_PIN`: Used in DHT11 tests (default: 4)

Override via command-line:
```bash
python3 test_sensors_unit.py --dht11 --pin 17
python3 test_sensors_unit.py --sht3x --addr 0x45
```

---

## Troubleshooting

### "No I2C devices found"
**Issue:** I2C bus not responding or no devices connected.

**Solutions:**
1. Check physical wiring:
   - SDA → GPIO2 (Pin 3)
   - SCL → GPIO3 (Pin 5)
   - GND → Pin 6
   - 3.3V → Pin 1

2. Verify I2C is enabled on Raspberry Pi:
   ```bash
   raspi-config  # Enable I2C under Interfacing Options
   ```

3. Check pull-up resistors (~4.7kΩ on SDA/SCL)

4. Test I2C directly:
   ```bash
   sudo i2cdetect -y 1  # Detect devices on bus 1
   ```

---

### "SHT3x test FAILED: Could not auto-detect SHT31d"
**Issue:** Sensor not responding or wrong I2C address.

**Solutions:**
1. Verify address with `--scan`:
   ```bash
   python3 test_sensors_unit.py --scan
   ```

2. Check ADDR pin connection:
   - ADDR → GND: address 0x44 (default)
   - ADDR → 3.3V: address 0x45
   - ADDR → floating: unpredictable

3. Try alternate address:
   ```bash
   python3 test_sensors_unit.py --sht3x --addr 0x45
   ```

---

### "SPS30 test FAILED: Could not open libsps30.so"
**Issue:** SPS30 driver library not built.

**Solutions:**
1. Build the driver:
   ```bash
   cd c_sps30_i2c
   bash RPI_DRIVER_BUILD.md  # Follow build instructions
   ```

2. Verify library exists:
   ```bash
   ls -la c_sps30_i2c/libsps30.so
   ```

---

### "DHT11 test FAILED: No module named 'adafruit_dht'"
**Issue:** CircuitPython DHT library not installed.

**Solutions:**
1. Install via pip:
   ```bash
   pip3 install adafruit-circuitpython-dht
   ```

2. Or install from repository:
   ```bash
   git clone https://github.com/adafruit/Adafruit_CircuitPython_DHT.git
   cd Adafruit_CircuitPython_DHT
   sudo python3 setup.py install
   ```

---

## Pre-Integration Validation Workflow

Before deploying the full system, validate hardware step-by-step:

```bash
# Step 1: Scan I2C bus
python3 test_sensors_unit.py --scan
# Expected: SHT3x at 0x44, SPS30 at 0x69

# Step 2: Test SHT3x individually
python3 test_sensors_unit.py --sht3x
# Expected: ✓ PASSED

# Step 3: Test SPS30 individually
python3 test_sensors_unit.py --sps30
# Expected: ✓ PASSED

# Step 4: Test DHT11 individually (if using)
python3 test_sensors_unit.py --dht11
# Expected: ✓ PASSED

# Step 5: Run comprehensive test
python3 test_sensors_unit.py --all
# Expected: All PASSED

# Step 6: Start full system
python3 sensor_reader.py
```

---

## Test Modes & Options

| Command | Purpose |
|---------|---------|
| `--scan` | Detect all I2C devices on bus |
| `--sht3x` | Test SHT3x sensor only |
| `--sps30` | Test SPS30 sensor only |
| `--dht11` | Test DHT11 sensor only |
| `--all` | Run all available tests |
| `--addr 0x45` | SHT3x alternate address |
| `--pin 17` | DHT11 alternate GPIO pin |
| `-n 5` / `--iterations 5` | Repeat reads N times |

---

## Advanced Testing

### Continuous Monitoring
Monitor sensor readings continuously:
```bash
while true; do
  python3 test_sensors_unit.py --sht3x --iterations 1
  sleep 5
done
```

### Performance Testing
Test sensor response with multiple rapid iterations:
```bash
python3 test_sensors_unit.py --sht3x --iterations 20
```

### Hardware Troubleshooting
Run comprehensive I2C diagnostics:
```bash
sudo apt-get install i2c-tools
sudo i2cdetect -y 1      # Detect I2C devices
sudo i2cdump -y 1 0x44   # Raw dump of SHT3x
```

---

## Exit Codes

- **0**: All tests passed
- **1**: Test failed (sensor not responding, wrong address, etc.)

Use in scripts:
```bash
python3 test_sensors_unit.py --sht3x
if [ $? -eq 0 ]; then
  echo "Sensor OK - starting system"
  python3 sensor_reader.py
else
  echo "Sensor FAILED - check hardware"
fi
```

---

## See Also

- `test_i2c_cli.py` - Original integrated test (all sensors together)
- `config.py` - Sensor configuration
- `sensor_reader.py` - Main data collection loop
- README.md - Hardware wiring & setup
