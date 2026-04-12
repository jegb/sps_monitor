# config.py

EMULATE = True
SENSOR_TYPE = "DHT11"  # Options: "DHT11", "SHT31", "SHT3X"
DHT11_PIN = 4          # GPIO pin for DHT11

# SHT3X Configuration (SHT30, SHT31, SHT35 variants)
# I2C Address: 0x44 (default, ADDR pin to GND) or 0x45 (ADDR pin to VDD)
# Power: 2.15V to 5.5V, 3.3V recommended