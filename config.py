# config.py

EMULATE = True
SENSOR_TYPE = "DHT11"  # Options: "DHT11", "SHT31", "SHT3X"
DHT11_PIN = 4          # GPIO pin for DHT11

# SHT3X Configuration (SHT30, SHT31, SHT35 variants)
# I2C Address: 0x44 (default, ADDR pin to GND) or 0x45 (ADDR pin to VDD)
# Power: 2.15V to 5.5V, 3.3V recommended

# PPD42 Dust Sensor Configuration (Optional)
PPD42_ENABLED = False           # Enable/disable PPD42 sensor
PPD42_PIN = 23                  # GPIO pin for PPD42 output
PPD42_PARTICLE_SIZE = 2.5       # Particle size in µm (2.5=PM2.5, 10=PM10, custom=other)
PPD42_SAMPLE_DURATION = 30      # Measurement duration in seconds