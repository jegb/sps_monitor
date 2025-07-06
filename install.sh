#!/bin/bash

echo "[1/7] Updating system..."
sudo apt update

echo "[2/7] Installing dependencies..."
sudo apt install -y python3 python3-pip python3-smbus build-essential git sqlite3

echo "[3/7] Installing Python libraries..."

echo "[3.1/7] Ensuring virtualenv is installed..."
sudo apt install -y python3-venv

echo "[3.2/7] Creating and activating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[3.3/7] Installing required Python packages inside venv..."
pip install --break-system-packages adafruit-circuitpython-dht paho-mqtt RPi.GPIO

echo "[3.4/7] Verifying Python packages installed..."
REQUIRED_PKG=(paho-mqtt adafruit-circuitpython-dht RPi.GPIO)
for pkg in "${REQUIRED_PKG[@]}"; do
  pip show "$pkg" > /dev/null || echo "Warning: $pkg not found"
done

if [ -f ~/sps30_monitor/c_sps30_i2c/libsps30.so ]; then
  echo "[4/7] Skipping build. Library already exists: ~/sps30_monitor/c_sps30_i2c/libsps30.so"
else
  echo "[4/7] Cloning and building Sensirion SPS30 driver in ~/embedded-sps..."
  cd ~
  git clone --recursive https://github.com/Sensirion/embedded-sps.git || true
  cd embedded-sps
  make release

  echo "[5/7] Locating built libsps30.so..."
  DRIVER_BUILD_PATH=$(find ~/embedded-sps/release -type f -name "libsps30.so" | head -n1)

  if [ -f "$DRIVER_BUILD_PATH" ]; then
    echo "[5/7] Copying $DRIVER_BUILD_PATH to ~/sps30_monitor/c_sps30_i2c/"
    cp "$DRIVER_BUILD_PATH" -v ~/sps30_monitor/c_sps30_i2c/
  else
    echo "❌ [5/7] libsps30.so not found. Build may have failed or output path changed."
    exit 1
  fi
fi

echo "[6/7] Cleaning up build directory..."
cd ~
rm -rf embedded-sps

echo "[7/7] Done. Activate virtual environment with 'source venv/bin/activate' before running sensor_reader.py"

echo "To enable systemd service:"
echo "  sudo cp sps30_reader.service /etc/systemd/system/"
echo "  sudo systemctl enable sps30_reader"
echo "  sudo systemctl start sps30_reader"
