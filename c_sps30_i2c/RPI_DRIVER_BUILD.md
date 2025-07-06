# 🛠️ Raspberry Pi SPS30 I²C Driver Build Guide (Sensirion Embedded-SPS)

This guide walks you through compiling the official `embedded-sps` driver for use with `sensor_reader.py` on different Raspberry Pi models.

---

## 📍 Supported Architectures

| Pi Model               | Architecture | Notes                          |
|------------------------|--------------|--------------------------------|
| Pi 3 / Pi 4 (32-bit)   | armv7        | Raspbian Lite / Desktop 32-bit |
| Pi 4 (64-bit OS)       | aarch64      | Raspberry Pi OS 64-bit         |
| Pi Zero 2 W            | armv6/v7     | Compatible with 32-bit builds  |

---

## 📦 Install Build Tools

Run this once:

```bash
sudo apt update
sudo apt install -y git build-essential
```

---

## 📂 Clone and Build the SPS30 Driver

```bash
git clone --recursive https://github.com/Sensirion/embedded-sps.git
cd embedded-sps
make release
```

This builds the shared object `libsps30.so` in the `release/` directory.

---

## 📁 Deploy Compiled Library

Copy the shared library to your project:

```bash
cp release/libsps30.so /home/pi/sps30_monitor/c_sps30_i2c/
```

> Adjust path as needed to match your directory.

---

## 🧪 Verify with Python

Run the CLI tester:

```bash
cd /home/pi/sps30_monitor/
python3 test_i2c_cli.py --read
```

---

## 🧠 Notes

- Ensure SEL pin on SPS30 is connected to **GND** to enable I²C mode.
- Use `uname -m` to confirm architecture (`armv7l` or `aarch64`).
- Rebuild the `.so` if moving to a different Pi model or OS variant.

---

## ❗ Troubleshooting

- If `libsps30.so` not found: ensure it's in the Python working directory.
- Use `ldd libsps30.so` to verify all dependencies are resolved.

