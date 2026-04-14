# 🔌 Raspberry Pi I²C Pinout & Configuration Reference

**Project:** SPS30 Air Quality Monitor with Temperature/Humidity Sensors
**Target Platform:** Raspberry Pi 3/4/5
**I²C Bus:** I²C-1 (GPIO2/GPIO3)
**Last Updated:** 2026-04-13

---

## 📍 RPI GPIO Pin Layout (40-Pin Header)

```
          RASPBERRY PI 40-PIN GPIO HEADER

          Left (ODD)      Right (EVEN)

    3V3  [1]  [2]  5V
    5V   [3]  [4]  5V
    GND  [5]  [6]  GND
    IO4  [7]  [8]  IO14
    GND  [9]  [10] IO15
    IO17 [11] [12] IO18
    IO27 [13] [14] GND
    IO22 [15] [16] IO23
    3V3  [17] [18] IO24
    IO10 [19] [20] GND
    IO9  [21] [22] IO25
    IO11 [23] [24] IO8
    GND  [25] [26] IO7
    ID_SD[27] [28] ID_SC
    IO5  [29] [30] GND
    IO6  [31] [32] IO12
    IO13 [33] [34] GND
    IO19 [35] [36] IO16
    IO26 [37] [38] IO20
    GND  [39] [40] IO21
```

**I²C Bus Pins (Highlighted for Your Project):**

| Function | Pin | Signal | Details |
|----------|-----|--------|---------|
| **3.3V Power** | 1, 17 | — | Max 500mA shared |
| **5V Power** | 2, 4 | — | Direct from USB |
| **I²C Data (SDA)** | **3** | **GPIO2** | **INTERNAL 1.8kΩ PULLUP** ← SPS30, SHT3X |
| **I²C Clock (SCL)** | **5** | **GPIO3** | **INTERNAL 1.8kΩ PULLUP** ← SPS30, SHT3X |
| **Ground** | 6, 9, 14, 20, 25, 30, 34, 39 | GND | Shared across all sensors |
| **DHT11 Data** | **11** | **GPIO17** | Single-wire protocol |

**Layout Guide:**
- Left column: **Odd** pins (1, 3, 5, 7, ... 39)
- Right column: **Even** pins (2, 4, 6, 8, ... 40)
- Power rails marked on outer edges (3V3, 5V, GND)

---

## 🎯 Quick Wiring Reference (This Project)

| Sensor | Signal | Connect To | Pin# | Details |
|--------|--------|-----------|------|---------|
| **SPS30** | VDD (5V) | Pin 2 (5V) | [2] | ⚠️ CRITICAL: 5V ONLY |
| **SPS30** | GND | Pin 6 (GND) | [6] | Any GND pin |
| **SPS30** | SDA | Pin 3 (GPIO2) | [3] | Shared I²C line |
| **SPS30** | SCL | Pin 5 (GPIO3) | [5] | Shared I²C line |
| **SPS30** | SEL | Pin 6 (GND) | [6] | Force I²C mode |
| **SHT3X** | VCC (3.3V) | Pin 1 (3.3V) | [1] | Optimal for I²C |
| **SHT3X** | GND | Pin 6 (GND) | [6] | Any GND pin |
| **SHT3X** | SDA | Pin 3 (GPIO2) | [3] | Shared I²C line |
| **SHT3X** | SCL | Pin 5 (GPIO3) | [5] | Shared I²C line |
| **SHT3X** | ADDR | Pin 6 (GND) | [6] | For address 0x44 |
| **SHT3X** | ADDR | Pin 1 (3.3V) | [1] | For address 0x45 |
| **DHT11** | VCC | Pin 1 (3.3V) | [1] | Recommended |
| **DHT11** | GND | Pin 6 (GND) | [6] | Any GND pin |
| **DHT11** | DATA | Pin 11 (GPIO17) | [11] | Single-wire protocol |

---

## 🔋 Power Distribution Map

### Available Power Rails

| Rail | Pin(s) | Current Limit | Notes |
|------|--------|---------------|-------|
| **3.3V** | 1, 17 | 500mA shared | Powers RPI logic, GPIO pull-ups |
| **5V** | 2, 4 | Unregulated | Direct from USB, no built-in limit; be careful |
| **GND** | 6, 9, 14, 20, 25, 30, 34, 39 | Infinite | All must be common ground |

### Current Budget

Typical consumption:
- RPI idle: ~200mA @ 5V
- GPIO logic: ~20mA
- I²C sensor suite (SPS30 + SHT3X): ~50–100mA combined

**Safe design margin:** Use a 2A+ power supply for safety.

---

## 📊 Sensor Pinout & I²C Address Mapping

### SPS30 (Particulate Matter Sensor)

**Sensor Connector Pinout (JST ZHR-5):**
```
Sensor Pin  │ Signal   │ RPI Pin          │ Voltage
────────────┼──────────┼──────────────────┼──────────
1           │ VDD      │ Pin 2 (5V)       │ 5.0V ± 5%
2           │ SDA      │ Pin 3 (GPIO2)    │ 3.3V logic
3           │ SCL      │ Pin 5 (GPIO3)    │ 3.3V logic
4           │ SEL      │ Pin 6 (GND)      │ Force I²C mode
5           │ GND      │ Pin 6 (GND)      │ Ground
```

| Property | Value |
|----------|-------|
| **I²C Address** | **0x69** (105 dec) |
| **Power** | 5.0V ONLY (4.75V–5.25V) |
| **Protocol** | I²C, Standard/Fast Mode (100–400 kHz) |
| **Startup Time** | ~8 seconds for data stabilization |
| **Pull-ups** | RPI internal (no external needed) |
| **Driver** | Pure Python I2C driver (architecture-independent) |

---

### SHT3X Family (Temperature & Humidity)

```
Sensor Pin  │ Signal   │ RPI Pin          │ Voltage
────────────┼──────────┼──────────────────┼──────────
1           │ VCC      │ Pin 1 (3.3V)     │ 3.3V (nom.)
2           │ GND      │ Pin 6 (GND)      │ Ground
3           │ SDA      │ Pin 3 (GPIO2)    │ 3.3V logic
4           │ SCL      │ Pin 5 (GPIO3)    │ 3.3V logic
5 (ADDR)    │ ADDR     │ Pin 6 or Pin 1   │ Selects address
```

| Property | Default (ADDR→GND) | Alternative (ADDR→VDD) |
|----------|-------------------|------------------------|
| **I²C Address** | 0x44 (68 dec) | 0x45 (69 dec) |
| **ADDR Pin** | Connect to GND (Pin 6) | Connect to 3.3V (Pin 1) |
| **Power** | 3.3V (Spec: 2.15V–5.5V) | 3.3V (Spec: 2.15V–5.5V) |
| **Protocol** | I²C, Standard/Fast Mode | I²C, Standard/Fast Mode |
| **Response Time** | <2s (temp), <8s (humidity) | <2s (temp), <8s (humidity) |

**Dual SHT3X Support:** Set one sensor to 0x44 (ADDR→GND) and another to 0x45 (ADDR→VDD) on the same bus.

---

### DHT11 (Temperature & Humidity, GPIO-based)

```
Sensor Pin  │ Signal   │ RPI Pin          │ Voltage
────────────┼──────────┼──────────────────┼──────────
1           │ VCC      │ Pin 1 (3.3V)     │ 3.3V–5.5V
2           │ DATA     │ Pin 11 (GPIO17)  │ 3.3V logic
3           │ (N/C)    │ (N/C)            │ —
4           │ GND      │ Pin 6 (GND)      │ Ground
```

| Property | Value |
|----------|-------|
| **Protocol** | Single-wire (NOT I²C) |
| **GPIO** | GPIO17 (Pin 11) |
| **Power** | 3.3V–5.5V (3.3V recommended) |
| **Pull-up Resistor** | 10kΩ (if module lacks internal pull-up) |
| **Mutual Exclusivity** | Cannot run DHT11 + SHT3X simultaneously (select in config.py) |

---

## ⚠️ Critical Voltage Rules

### 🔴 MUST DO

1. **SPS30 VDD → Pin 2 (5V) ONLY**
   - Do NOT use Pin 1 (3.3V)
   - Sensor will not power up or will be unreliable
   - I²C data lines are 3.3V tolerant internally (no level shifter needed)

2. **SHT3X VCC → Pin 1 (3.3V)**
   - Spec allows 2.15V–5.5V, but 3.3V is optimal for I²C
   - Improves I²C signal quality
   - Reduces power consumption

3. **DHT11 VCC → Pin 1 (3.3V) or Pin 2 (5V)**
   - Pin 1 (3.3V) preferred for logic-level compatibility
   - Pin 2 (5V) works but consumes slightly more power

4. **All GND → Pins 6, 9, 14, 20, 25, 30, 34, 39 (any GND)**
   - Common ground is critical for I²C communication
   - Use separate GND pins for different sensor groups if possible

### 🔵 MUST NOT DO

- ❌ Do NOT exceed 500mA on 3.3V rail (Pin 1, 17)
- ❌ Do NOT connect SPS30 to 3.3V
- ❌ Do NOT add external pull-up resistors to SDA/SCL (internal 1.8kΩ sufficient)
- ❌ Do NOT connect I²C signals (SDA, SCL) to 5V directly
- ❌ Do NOT mix 5V and 3.3V logic on the same GPIO (level shifter required)
- ❌ Do NOT use DHT11 and SHT3X sensors simultaneously in current config

---

## 🧪 I²C Bus Verification Checklist

**Before powering on, verify:**

- [ ] **SPS30 VDD** connected to Pin 2 (5V)
- [ ] **SHT3X VCC** connected to Pin 1 (3.3V)
- [ ] **DHT11 VCC** connected to Pin 1 (3.3V) or Pin 2 (5V)
- [ ] **All GND** connected to RPI GND pins (6, 9, 14, 20, 25, 30, 34, 39)
- [ ] **SDA (GPIO2, Pin 3)** connected to SPS30 SDA and SHT3X SDA
- [ ] **SCL (GPIO3, Pin 5)** connected to SPS30 SCL and SHT3X SCL
- [ ] **SPS30 SEL** connected to GND (Pin 6 or 9)
- [ ] **SHT3X ADDR** set correctly (GND for 0x44, VDD for 0x45)
- [ ] **DHT11 DATA** connected to GPIO17 (Pin 11)
- [ ] **No external pull-ups** on SDA/SCL
- [ ] **No jumpers or bridges** across adjacent pins

**After power-on, test with:**
```bash
python3 test_sensors_unit.py --scan      # List detected I2C devices
python3 test_sensors_unit.py --sps30     # Test SPS30
python3 test_sensors_unit.py --sht3x     # Test SHT3X
python3 test_sensors_unit.py --dht11     # Test DHT11
```

---

## 📈 I²C Address Space (0x00–0x7F)

```
I²C Address Allocation Table:

0x00–0x07  │ Reserved (general call)
0x08–0x77  │ Usable device addresses
0x78–0x7F  │ Reserved (device IDs)

Active Addresses (This Project):
├─ 0x44 (68 dec)  │ SHT3X (ADDR→GND) ✓
├─ 0x45 (69 dec)  │ SHT3X (ADDR→VDD) ✓
├─ 0x69 (105 dec) │ SPS30 ✓
└─ (others)       │ Available for expansion

Status: ✅ NO COLLISIONS
All three sensors use unique addresses.
```

---

## 🔧 Hardware Troubleshooting

### Symptom: "No I²C devices found"

**Likely causes:**
1. I²C not enabled in raspi-config
2. GPIO2/GPIO3 shorted or damaged
3. Wrong wiring (check pinout again)
4. Sensor power not connected

**Fix:**
```bash
# Enable I²C
sudo raspi-config
# → Interface Options → I2C → Enable

# Test I²C bus
i2cdetect -y 1

# Test specific address
i2cget -y 1 0x68
```

### Symptom: "I²C device at 0x69 but SPS30 test fails"

**Likely causes:**
1. SEL pin not connected to GND (forces SPI mode)
2. SPS30 power at 3.3V instead of 5V
3. SDA/SCL shorted together
4. Data line noise from long wires

**Fix:**
- Verify SPS30 SEL pin on GND
- Check 5V voltage with multimeter (should be 4.75V–5.25V)
- Use short, twisted-pair wires for SDA/SCL
- Pure Python driver works across all RPi models (RPi Zero, 2, 3, 4, 5)

### Symptom: "SHT3X at 0x44 but returns garbage data"

**Likely causes:**
1. Power at wrong voltage (not 3.3V)
2. I²C pull-ups too strong (unlikely, RPI internal are 1.8kΩ)
3. Clock speed too fast
4. Data line capacitance too high

**Fix:**
- Verify VCC at 3.3V with multimeter
- Reduce I²C speed to 100 kHz in config
- Shorten SDA/SCL wires
- Check for external pull-up resistors (remove if found)

---

## 📚 Reference Documents

- **RPI Official Pinout:** https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- **I²C Specification:** https://en.wikipedia.org/wiki/I2C
- **SPS30 Datasheet:** https://sensirion.com/products/catalog/SPS30/
- **SHT3X Datasheet:** https://sensirion.com/products/catalog/SHT30/
- **DHT11 Datasheet:** https://www.mouser.com/datasheet/2/758/DHT11-9142_12_15_2018-1024x1024.pdf

---

**✅ Ready to wire!** Follow the pinout tables above and verify with the checklist before power-on.
