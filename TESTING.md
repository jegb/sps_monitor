# Sensor Testing & Validation Guide

Complete reference for hardware validation and sensor diagnostics.

---

## Quick Reference

### Common Commands

```bash
# I2C bus scan
python3 test_sensors_unit.py --scan

# Test individual sensors
python3 test_sensors_unit.py --sht3x              # SHT3x (I2C)
python3 test_sensors_unit.py --sps30              # SPS30 (I2C)
python3 test_sensors_unit.py --dht11              # DHT11 (GPIO)

# Test all sensors
python3 test_sensors_unit.py --all

# Custom options
python3 test_sensors_unit.py --sht3x --addr 0x45  # Alternate I2C address
python3 test_sensors_unit.py --dht11 --pin 17     # Alternate GPIO pin
python3 test_sensors_unit.py --sps30 -n 3         # 3 iterations
```

---

## I2C Bus Scan

Detect all connected I2C devices on the bus:

```bash
python3 test_sensors_unit.py --scan
```

**Expected output:**
```
============================================================
I2C BUS SCAN
============================================================
Address      Hex      Device
--------------------------------------------------
0x44         0x44     SHT3X (default addr, ADDR→GND)
0x69         0x69     SPS30

Found 2 device(s).
```

**Alternative tools:**
```bash
# Using i2c-tools
sudo apt-get install i2c-tools
sudo i2cdetect -y 1                    # Scan I2C bus 1
sudo i2cdump -y 1 0x44                 # Raw dump of device at 0x44
```

---

## Individual Sensor Tests

### SHT3x Sensor (Temperature/Humidity, I2C)

Test the SHT3x family (SHT30, SHT31, SHT35) on I2C.

**Default address (ADDR pin → GND):**
```bash
python3 test_sensors_unit.py --sht3x
```

**Alternate address (ADDR pin → 3.3V):**
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

### SPS30 Sensor (Particulate Matter, I2C)

Test the SPS30 on I2C at address 0x69.

**Architecture-independent:** Uses pure Python I2C driver (works on all RPi models: Zero, 2, 3, 4, 5).

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
Using pure Python I2C driver
Starting SPS30 measurement sequence...
(SPS30 requires stabilization time)

Attempt     PM1.0        PM2.5        PM4.0        PM10.0       Status
--------------------------------------------------------------------------------
Waking up sensor...
Starting measurement...
Waiting for data ready...
Data ready!
Reading measurement data...
Read 20 words successfully
1           2.34         5.67         8.90         12.34        ✓ OK
2           2.35         5.68         8.91         12.35        ✓ OK

✓ SPS30 test PASSED
```

**Notes:**
- SPS30 requires ~8-10 seconds for stabilization
- Pure Python driver eliminates C library compilation
- Works identically across all Raspberry Pi architectures (32-bit and 64-bit)

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

**Notes:**
- DHT11 has 2-second minimum read interval
- Tests automatically wait between iterations

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

## Pre-Deployment Checklist

Run this workflow before starting the full system:

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

**Checklist:**
- [ ] SPS30 sensor physically connected (5V, GND, SDA, SCL, SEL→GND)
- [ ] SHT3x sensor physically connected (3.3V, GND, SDA, SCL, ADDR)
- [ ] DHT11 sensor physically connected (3.3V, GND, DATA→GPIO17) [if using]
- [ ] Raspberry Pi I2C enabled (`sudo raspi-config` → Interfacing Options → I2C → Enable)
- [ ] `python3 test_sensors_unit.py --scan` shows expected devices
- [ ] `python3 test_sensors_unit.py --sht3x` → ✓ PASSED
- [ ] `python3 test_sensors_unit.py --sps30` → ✓ PASSED
- [ ] `python3 test_sensors_unit.py --dht11` → ✓ PASSED [if using]
- [ ] `python3 test_sensors_unit.py --all` → all PASSED
- [ ] `config.py` updated with correct `SENSOR_TYPE`

---

## I2C Address Reference

| Sensor | Default Address | Alternate Address | Notes |
|--------|-----------------|-------------------|-------|
| SHT3x  | 0x44 (ADDR→GND) | 0x45 (ADDR→3.3V) | Allows 2 sensors on same bus |
| SPS30  | **0x69** | N/A | Fixed I2C address |

**No address collisions** - All sensors use unique addresses.

---

## Troubleshooting

### "No I2C devices found"

**Issue:** I2C bus not responding or no devices connected.

**Solutions:**

1. **Check physical wiring:**
   - SDA → GPIO2 (Pin 3)
   - SCL → GPIO3 (Pin 5)
   - GND → Pin 6
   - Power (3.3V or 5V depending on sensor)

2. **Verify I2C is enabled:**
   ```bash
   sudo raspi-config
   # → Interfacing Options → I2C → Enable
   sudo reboot
   ```

3. **Test I2C directly:**
   ```bash
   sudo i2cdetect -y 1
   ```

4. **Check for hardware issues:**
   - Verify power supply voltage with multimeter
   - Check for loose connections
   - Inspect for damaged wires or pins

---

### "SHT3x test FAILED: Could not auto-detect SHT31d"

**Issue:** Sensor not responding or wrong I2C address.

**Solutions:**

1. **Verify address with scan:**
   ```bash
   python3 test_sensors_unit.py --scan
   ```

2. **Check ADDR pin connection:**
   - ADDR → GND: address 0x44 (default)
   - ADDR → 3.3V: address 0x45
   - ADDR → floating: unpredictable

3. **Try alternate address:**
   ```bash
   python3 test_sensors_unit.py --sht3x --addr 0x45
   ```

4. **Verify power:**
   - SHT3x VCC → Pin 1 (3.3V)
   - Measure with multimeter: should be 3.0V–3.6V

---

### "SPS30 test FAILED" or "Timeout"

**Issue:** SPS30 not responding on I2C bus.

**Solutions:**

1. **Verify correct I2C address (0x69):**
   ```bash
   python3 test_sensors_unit.py --scan
   # Should show: 0x69         0x69     SPS30
   ```

2. **Check SEL pin:**
   - SPS30 SEL pin MUST be connected to GND
   - Without this, sensor defaults to SPI mode (not I2C)

3. **Verify power:**
   - SPS30 VDD → Pin 2 (5V) - **CRITICAL: 5V ONLY**
   - Do NOT use 3.3V - sensor will not work
   - Measure with multimeter: should be 4.75V–5.25V

4. **Check wiring:**
   ```
   SPS30 Pin 1 (VDD) → RPI Pin 2 (5V)
   SPS30 Pin 2 (SDA) → RPI Pin 3 (GPIO2)
   SPS30 Pin 3 (SCL) → RPI Pin 5 (GPIO3)
   SPS30 Pin 4 (SEL) → RPI Pin 6 (GND)
   SPS30 Pin 5 (GND) → RPI Pin 6 (GND)
   ```

5. **Architecture compatibility:**
   - The pure Python driver works on all RPi models
   - No compilation needed
   - If you see "C library driver" in output, you're using the old driver

---

### "DHT11 test FAILED: No module named 'adafruit_dht'"

**Issue:** CircuitPython DHT library not installed.

**Solutions:**

1. **Install via pip:**
   ```bash
   pip3 install adafruit-circuitpython-dht
   ```

2. **Verify GPIO pin:**
   - DHT11 DATA → GPIO17 (Pin 11) by default
   - Can be changed with `--pin` option

3. **Check pull-up resistor:**
   - Some DHT11 modules lack internal pull-up
   - Add 10kΩ resistor between DATA and 3.3V if needed

---

## Command-Line Options

| Option | Purpose | Example |
|--------|---------|---------|
| `--scan` | Detect all I2C devices on bus | `--scan` |
| `--sht3x` | Test SHT3x sensor only | `--sht3x` |
| `--sps30` | Test SPS30 sensor only | `--sps30` |
| `--dht11` | Test DHT11 sensor only | `--dht11` |
| `--all` | Run all available tests | `--all` |
| `--addr 0x45` | SHT3x alternate address | `--sht3x --addr 0x45` |
| `--pin 17` | DHT11 alternate GPIO pin | `--dht11 --pin 17` |
| `-n 5` / `--iterations 5` | Repeat reads N times | `--sps30 -n 5` |

---

## Performance Baseline

| Sensor | Response Time | Min Read Interval | Notes |
|--------|---------------|-------------------|-------|
| SHT3x | <2 sec (temp), <8 sec (humidity) | 0 sec | Fast, no cooldown |
| SPS30 | ~8-10 sec | 8-10 sec | Requires stabilization |
| DHT11 | Variable | 2 sec | Hardware timing constraint |

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

### Scripted Validation

Use exit codes for automation:
```bash
python3 test_sensors_unit.py --sht3x
if [ $? -eq 0 ]; then
  echo "Sensor OK - starting system"
  python3 sensor_reader.py
else
  echo "Sensor FAILED - check hardware"
fi
```

**Exit codes:**
- **0**: All tests passed
- **1**: Test failed (sensor not responding, wrong address, etc.)

---

## See Also

- [RPI_I2C_PINOUT_REFERENCE.md](RPI_I2C_PINOUT_REFERENCE.md) - Complete wiring diagrams and pinouts
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation and deployment
- [README.md](README.md) - Project overview
- `config.py` - Sensor configuration
- `sensor_reader.py` - Main data collection loop
