# 🌫️ SPS30 Air Quality Monitor – Raspberry Pi Edition

This project uses the Sensirion SPS30 (I²C) with optional SHT31 or DHT11 to monitor PM1.0, PM2.5, PM4.0, PM10, temperature, and humidity. Data is logged to SQLite and published via MQTT to Node-RED for visualization.

---

## 📦 Features

- SPS30 readings via official C driver wrapped in Python (I²C)
- Modular sensor support for temperature and humidity (DHT11, SHT31)
- SQLite database storage with rotation options
- **Web dashboard** with live + historical data visualization (Flask)
- MQTT publishing for Node-RED integration
- Optional systemd service for auto-start on boot
- CLI tool for testing I²C + sensor integration

---

## 🚀 Setup Instructions After Cloning This Project

Clone the repository and navigate into it:

```bash
git clone https://github.com/your-username/sps30_monitor.git
cd sps30_monitor
```

Make the installation script executable:

```bash
chmod +x install.sh
```

Then run it:

```bash
./install.sh
```

This will:
- Install Python and system dependencies
- Build and install Sensirion SPS30 driver
- Copy compiled `libsps30.so` to `c_sps30_i2c/`
- Clean up build directories

Test the setup:

```bash
python3 test_i2c_cli.py --read
```

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


---

## ⚠️ Disclaimer

This project is provided for educational and prototyping purposes only.

> **Use at your own risk.**  
> The authors and contributors assume no responsibility or liability for damage to hardware, health, or environment resulting from the use or misuse of this software and wiring setup. Always double-check voltage levels, connections, and sensor datasheets before powering your circuit.

