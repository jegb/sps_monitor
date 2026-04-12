# Sensor Testing Quick Reference

## Test Tools Overview

| Tool | Purpose | Usage |
|------|---------|-------|
| `test_sensors_unit.py` | **Individual sensor probing & validation** | `python3 test_sensors_unit.py --sht3x` |
| `test_i2c_cli.py` | Integrated test (all sensors together) | `python3 test_i2c_cli.py --read` |

---

## Common Commands

### Diagnose Hardware Issues

```bash
# Scan I2C bus for connected devices
python3 test_sensors_unit.py --scan

# Expected output:
# Address      Hex      Device
# 0x44         0x44     SHT3X (default addr, ADDR→GND)
# 0x69         0x69     SPS30
```

### Test Individual Sensors

```bash
# Test SHT3x (I2C Temperature/Humidity)
python3 test_sensors_unit.py --sht3x

# Test with alternate I2C address (ADDR→3.3V)
python3 test_sensors_unit.py --sht3x --addr 0x45

# Test SPS30 (I2C Particulate Matter)
python3 test_sensors_unit.py --sps30

# Test DHT11 (GPIO Temperature/Humidity)
python3 test_sensors_unit.py --dht11

# Test DHT11 on different GPIO pin
python3 test_sensors_unit.py --dht11 --pin 17
```

### Run Multiple Iterations

```bash
# Read SHT3x 5 times
python3 test_sensors_unit.py --sht3x --iterations 5

# Read SPS30 3 times (waits ~10 sec between reads)
python3 test_sensors_unit.py --sps30 --iterations 3
```

### Full System Validation

```bash
# Test all sensors at once
python3 test_sensors_unit.py --all

# Test all & check exit code (0=passed, 1=failed)
python3 test_sensors_unit.py --all && echo "READY" || echo "FAILED"
```

---

## Pre-Integration Checklist

- [ ] SPS30 sensor physically connected (5V, GND, SDA, SCL)
- [ ] SHT3x sensor physically connected (3.3V, GND, SDA, SCL, ADDR)
- [ ] DHT11 sensor physically connected (if using)
- [ ] Raspberry Pi I2C enabled (`raspi-config`)
- [ ] Run: `python3 test_sensors_unit.py --scan` → shows devices
- [ ] Run: `python3 test_sensors_unit.py --sht3x` → ✓ PASSED
- [ ] Run: `python3 test_sensors_unit.py --sps30` → ✓ PASSED
- [ ] Run: `python3 test_sensors_unit.py --dht11` → ✓ PASSED (if using)
- [ ] Run: `python3 test_sensors_unit.py --all` → all PASSED
- [ ] Update `config.py` with correct `SENSOR_TYPE`
- [ ] Run: `python3 test_i2c_cli.py --read` → integrated test passes
- [ ] Run: `python3 sensor_reader.py` → data collection starts

---

## I2C Address Reference

| Sensor | Default Address | Alternate Address | Notes |
|--------|-----------------|-------------------|-------|
| SHT3x  | 0x44 (ADDR→GND) | 0x45 (ADDR→3.3V) | Allows 2 sensors on same bus |
| SPS30  | 0x69 | N/A | Only I2C interface |

---

## Troubleshooting Quick Fixes

### I2C bus shows no devices
```bash
# Check I2C is enabled
sudo raspi-config  # Enable I2C under Interfacing Options

# Verify physically
sudo i2cdetect -y 1
```

### SHT3x not found at 0x44
```bash
# Try alternate address
python3 test_sensors_unit.py --sht3x --addr 0x45

# Verify ADDR pin connection:
# - If ADDR→GND, use 0x44
# - If ADDR→3.3V, use 0x45
```

### SPS30 driver not found
```bash
# Build driver
cd c_sps30_i2c
bash RPI_DRIVER_BUILD.md
cd ..
```

### DHT11 not responding
```bash
# Install library
pip3 install adafruit-circuitpython-dht

# Verify GPIO pin and add pull-up resistor (10kΩ DATA→3.3V)
python3 test_sensors_unit.py --dht11 --pin 4
```

---

## Performance Baseline

| Sensor | Response Time | Min Read Interval |
|--------|---------------|-------------------|
| SHT3x | <2 sec (temp), <8 sec (humidity) | 0 sec |
| SPS30 | 8-10 sec | 8-10 sec |
| DHT11 | Variable | 2 sec |

---

## See Full Documentation

```bash
cat TESTING.md
```
