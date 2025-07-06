#!/bin/bash

echo "[1/5] Updating system..."
sudo apt update

echo "[2/5] Installing dependencies..."
sudo apt install -y python3 python3-pip python3-smbus build-essential git sqlite3

echo "[3/5] Installing Python libraries..."

echo "[3.1/5] Ensuring virtualenv is installed..."
sudo apt install -y python3-venv

echo "[3.2/5] Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[3.3/5] Installing required Python packages inside venv..."
pip install --break-system-packages adafruit-circuitpython-dht Adafruit_DHT paho-mqtt RPi.GPIO

echo "[3.4/5] Verifying Python packages installed..."
REQUIRED_PKG=(paho-mqtt adafruit-circuitpython-dht Adafruit_DHT RPi.GPIO)
for pkg in "${REQUIRED_PKG[@]}"; do
  pip show "$pkg" > /dev/null || echo "Warning: $pkg not found"
done

echo "[4/5] Using prebuilt SPS30 driver library included in the distribution."

echo "[5/5] Done. Activate virtual environment with 'source venv/bin/activate' before running sensor_reader.py"

echo "To enable systemd service:"
echo "  sudo cp sps30_reader.service /etc/systemd/system/"
echo "  sudo systemctl enable sps30_reader"
echo "  sudo systemctl start sps30_reader"
