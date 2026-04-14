# Raspberry Pi Zero Compatibility Analysis

**Question:** Is the I²C configuration compatible with Raspberry Pi Zero?

**Short Answer:** ✅ **YES, with caveats.** Hardware pinout is identical, but performance and power considerations differ.

---

## 🔧 GPIO & I²C Compatibility

| Feature | Pi Zero | Pi Zero 2W | Pi 3/4/5 | Status |
|---------|---------|-----------|----------|--------|
| **GPIO Header** | 40-pin | 40-pin | 40-pin | ✅ IDENTICAL |
| **I²C-1 Bus** | GPIO2 (SDA), GPIO3 (SCL) | GPIO2 (SDA), GPIO3 (SCL) | GPIO2 (SDA), GPIO3 (SCL) | ✅ IDENTICAL |
| **Pull-ups** | 1.8kΩ internal | 1.8kΩ internal | 1.8kΩ internal | ✅ IDENTICAL |
| **I²C Speed** | 100/400 kHz | 100/400 kHz | 100/400 kHz | ✅ IDENTICAL |
| **Pin Layout** | 1-40 standard | 1-40 standard | 1-40 standard | ✅ IDENTICAL |
| **GPIO17 (DHT11)** | ✅ Available | ✅ Available | ✅ Available | ✅ IDENTICAL |

**Conclusion:** ✅ **Pinout and I²C bus are 100% compatible.** No hardware changes needed.

---

## ⚡ Power Delivery Differences

### SPS30 Power Requirements

| Sensor | Requirement | Pi Zero | Pi Zero 2W | Pi 3/4/5 | Status |
|--------|------------|---------|-----------|----------|--------|
| **SPS30** | 5.0V ± 5% @ ~100mA | ✅ OK | ✅ OK | ✅ OK | Uses USB 5V directly |
| **SHT3X** | 3.3V @ ~3mA | ⚠️ Consider | ✅ OK | ✅ OK | Shared 3.3V rail |
| **DHT11** | 3.3V or 5V @ ~2mA | ⚠️ Consider | ✅ OK | ✅ OK | Shared 3.3V rail |

### 3.3V Rail Budget

| Component | Pi Zero | Pi Zero 2W | Pi 3/4/5 |
|-----------|---------|-----------|----------|
| RPI Logic | ~100mA | ~150mA | ~200mA |
| SHT3X | ~3mA | ~3mA | ~3mA |
| DHT11 | ~2mA | ~2mA | ~2mA |
| **Total** | ~105mA | ~155mA | ~205mA |
| **Available** | 500mA | 500mA | 500mA |
| **Headroom** | ✅ 395mA | ✅ 345mA | ✅ 295mA |

**Conclusion:** ✅ **3.3V rail has sufficient headroom** even on Pi Zero (original).

---

## 💻 CPU & Performance Considerations

### Processor Architecture

| Model | CPU | Cores | Speed | Notes |
|-------|-----|-------|-------|-------|
| **Pi Zero** | ARM1176JZF-S | 1 | 1.0 GHz | Original—slower but adequate for sensors |
| **Pi Zero 2W** | ARM Cortex-A53 | 4 | 1.5 GHz | **Recommended for this project** |
| **Pi 3** | ARM Cortex-A53 | 4 | 1.4 GHz | Original Pi 3 (not Plus) |
| **Pi 4** | ARM Cortex-A72 | 4 | 1.8 GHz | Best performance |
| **Pi 5** | ARM Cortex-A76 | 4 | 2.4 GHz | Fastest |

### Workload Analysis for SPS Monitor

Tasks running simultaneously:
1. **I²C sensor reads** (every 60 seconds)
   - SPS30: ~10 seconds (blocking)
   - SHT3X/DHT11: <1 second
   - CPU: ~30% for 10 seconds

2. **Database writes** (SQLite)
   - CPU: ~5% for <100ms

3. **MQTT publishing**
   - CPU: ~2% for <100ms

4. **Web server** (Flask)
   - Idle: ~0%
   - Request handling: ~10-20%

5. **System services**
   - Idle: ~10-15%

### Can Pi Zero Handle This?

| Component | Pi Zero | Pi Zero 2W | Pi 3/4/5 | Notes |
|-----------|---------|-----------|----------|-------|
| **I²C sensor reads** | ✅ Yes | ✅ Yes | ✅ Yes | Sequential; not CPU intensive |
| **Database logging** | ✅ Yes | ✅ Yes | ✅ Yes | Fast SSD-like performance |
| **MQTT publishing** | ✅ Yes | ✅ Yes | ✅ Yes | Network I/O, not CPU bound |
| **Web dashboard** | ⚠️ Marginal | ✅ Yes | ✅ Yes | Can be slow under load |
| **All simultaneously** | ⚠️ Slow | ✅ Good | ✅ Excellent | Performance varies |

**Conclusion:**
- ✅ **Pi Zero (original):** Can run the project, but single-core may struggle if multiple web requests arrive during sensor read. Acceptable for low-traffic scenarios.
- ✅ **Pi Zero 2W:** Recommended. 4 cores handle concurrent requests + sensor reads smoothly.
- ✅ **Pi 3/4/5:** Best performance, no concerns.

---

## 📋 Pi Zero Deployment Checklist

### Hardware Requirements

- [ ] Raspberry Pi Zero 2W **OR** Pi Zero (original, if accepting slower web dashboard)
- [ ] 40-pin GPIO header installed (or soldered)
- [ ] 5V power supply (minimum 2A recommended)
- [ ] SPS30 sensor (I²C)
- [ ] SHT3X or DHT11 (temp/humidity)
- [ ] Short jumper wires (<30cm)

### Software Considerations

**Pi Zero Headaches:**
1. **No WiFi on original Pi Zero** — Use USB WiFi adapter or USB-to-Ethernet
2. **Single-core performance** — Web dashboard may freeze briefly during sensor reads
3. **Slower Flask server** — Accept 1-2 second response times on low-end hardware
4. **No X11 display** — Must use web dashboard or SSH for monitoring

**Pi Zero 2W Advantages:**
1. **WiFi built-in** — Works like Pi 3/4/5
2. **4 cores** — Handles concurrent requests
3. **Faster Python execution** — Sensor reads don't block web server
4. **Better stability** — Systemd services run smoothly

### Recommended Configuration for Pi Zero

```python
# config.py adjustments for Pi Zero (original)

EMULATE = False  # Use real sensors

# Increase read interval to reduce CPU load
SENSOR_READ_INTERVAL = 90  # Instead of 60 seconds

# Optional: Reduce Flask workers if using original Pi Zero
# FLASK_WORKERS = 1  # Single worker to save memory
```

### Installation Notes

**Important:** Pi Zero variants support different architectures:

| Pi Model | Architecture | Install Notes |
|----------|--------------|---------------|
| **Pi Zero** | armv6 | Use Raspbian Lite (32-bit). Some packages may not support armv6. |
| **Pi Zero W/2W** | armv7 / armv8 | Standard 32-bit Raspbian compatible. 64-bit OS available for Zero 2W. |
| **Pi 3/4/5** | armv8 | 32-bit or 64-bit Raspbian. 64-bit recommended. |

**Known Issues:**
- Some Python packages (esp. NumPy/SciPy) may be slow to compile on Pi Zero
- Pre-built wheels may not be available for armv6
- Build `libsps30.so` may take longer (~5-10 minutes on Pi Zero)

---

## 🎯 Recommendation Matrix

**Choose based on your use case:**

```
USE Pi ZERO (original) IF:
  ✓ Budget is extremely limited
  ✓ Sensors are stable/predictable (low traffic)
  ✓ You can accept slow web dashboard
  ✓ Prefer wired Ethernet over WiFi
  ✗ NOT recommended for production monitoring

USE Pi ZERO 2W IF:
  ✓ Want built-in WiFi
  ✓ Need responsive web dashboard
  ✓ Running concurrent services (MQTT + web)
  ✓ Acceptable performance/cost balance
  ✓ RECOMMENDED for this project

USE Pi 3/4/5 IF:
  ✓ Need maximum performance
  ✓ Expect high web dashboard traffic
  ✓ Running additional services
  ✓ Production deployment
  ✓ Future-proofing
```

---

## ✅ I²C Configuration Status for Pi Zero

### Pinout: ✅ **100% Compatible**

The pinout tables in `RPI_I2C_PINOUT_REFERENCE.md` apply directly to Pi Zero:

```
Pi Zero 40-pin GPIO Header (IDENTICAL to Pi 3/4/5):

          Left (ODD)      Right (EVEN)

    3V3  [1]  [2]  5V
    5V   [3]  [4]  5V
    GND  [5]  [6]  GND
    ...
    IO17 [11] [12] IO18
    ...
```

### Address Allocation: ✅ **No Changes**

| Sensor | Address | Bus | Status |
|--------|---------|-----|--------|
| SPS30 | 0x68 | I²C-1 | ✅ Identical |
| SHT3X | 0x44/0x45 | I²C-1 | ✅ Identical |
| DHT11 | GPIO17 | GPIO | ✅ Identical |

### Pull-ups: ✅ **No Changes**

- GPIO2 (SDA): 1.8kΩ internal pull-up ✅
- GPIO3 (SCL): 1.8kΩ internal pull-up ✅
- No external pull-ups needed ✅

---

## 🚀 Deploying to Pi Zero

### Step 1: Verify Hardware

```bash
# Check Pi model
cat /proc/device-tree/model

# Check architecture
uname -m   # Should show armv6l or armv7l or aarch64

# Enable I²C
sudo raspi-config
# Interface Options → I2C → Enable
```

### Step 2: Install Dependencies

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install I2C tools (verify hardware first)
sudo apt-get install -y i2c-tools python3-dev python3-pip

# Install sensor libraries
pip3 install adafruit-circuitpython-busio \
             adafruit-circuitpython-sht31d \
             adafruit-circuitpython-dht \
             paho-mqtt flask
```

### Step 3: Build SPS30 Driver

```bash
# Compile driver for armv6/armv7
cd c_sps30_i2c
gcc -fPIC -shared -o libsps30.so \
  sps30.c sensirion_common.c hw_i2c/sensirion_hw_i2c_implementation.c \
  -I. -Ihw_i2c
cd ..
```

### Step 4: Run Hardware Tests

```bash
# Test I2C bus
python3 test_sensors_unit.py --scan

# Test sensors
python3 test_sensors_unit.py --all
```

### Step 5: Start Services

```bash
# Initialize database
python3 init_sps30_db.py

# Start data collection (background)
nohup python3 sensor_reader.py > sensor_reader.log 2>&1 &

# Start web dashboard (background)
nohup python3 web_server.py --port 5000 > web_server.log 2>&1 &

# Access dashboard
# http://<pi-zero-ip>:5000
```

---

## ⚠️ Known Limitations (Pi Zero)

1. **Slower I²C communication** — Not a problem; sensors are slow
2. **Web dashboard response time** — May lag 1-2 seconds on Pi Zero (original)
3. **No simultaneous high-load activity** — Single-core limitation
4. **Memory constraints** — Pi Zero has 512MB-1GB RAM (adequate for this project)
5. **No video output by default** — Use headless setup (SSH or web dashboard)

---

## 🎓 Summary

| Question | Answer |
|----------|--------|
| Can Pi Zero use this I²C config? | ✅ Yes, pinout is identical |
| Do I need to change pinout wiring? | ✅ No, use same pin numbers |
| Do I need external pull-ups? | ❌ No, internal pull-ups work |
| Which Pi Zero variant is best? | ⚠️ **Pi Zero 2W recommended**, original Pi Zero OK |
| Will the web dashboard work? | ✅ Yes, but may be slow on original Pi Zero |
| Is 3.3V power sufficient? | ✅ Yes, ~105mA total usage vs 500mA available |
| Can I use Pi Zero instead of Pi 3/4? | ⚠️ Yes, but performance is slower. Use 2W for best results. |

---

**Verdict:** ✅ **Fully compatible with Pi Zero 2W. Compatible but slower with original Pi Zero.**

Recommend **Pi Zero 2W** for this project due to:
- 4-core processor
- Built-in WiFi
- Better responsive web dashboard
- Better handling of concurrent requests
- Similar cost to adding WiFi adapter to original Pi Zero
