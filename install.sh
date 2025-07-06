#!/bin/bash

echo "[1/7] Updating system..."
sudo apt update

echo "[2/7] Installing dependencies..."
sudo apt install -y python3 python3-pip python3-smbus build-essential git sqlite3

echo "[3/7] Installing Python libraries..."
pip3 install adafruit-circuitpython-dht paho-mqtt RPi.GPIO

echo "[4/7] Cloning and building Sensirion SPS30 driver in ~/embedded-sps..."
cd ~
git clone --recursive https://github.com/Sensirion/embedded-sps.git || true
cd embedded-sps
make release

echo "[5/7] Copying built library to project folder..."
cp release/libsps30.so -v ~/sps30_monitor/c_sps30_i2c/

echo "[6/7] Cleaning up build directory..."
cd ~
rm -rf embedded-sps

echo "[7/7] Done. You can now start the system or run test_i2c_cli.py --read"

echo "To enable systemd service:"
echo "  sudo cp sps30_reader.service /etc/systemd/system/"
echo "  sudo systemctl enable sps30_reader"
echo "  sudo systemctl start sps30_reader"
