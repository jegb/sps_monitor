import sys
# Import board FIRST to ensure busio gets the right one
from adafruit_blinka.board.raspberrypi import raspi_40pin
sys.modules['board'] = raspi_40pin

import busio
import adafruit_sht31d
from adafruit_blinka.board.raspberrypi.raspi_40pin import SCL, SDA

def get_readings():
    """
    Read temperature and humidity from SHT3x sensor.
    Works with SHT30, SHT31, and SHT35 variants via I2C.
    Default address: 0x44 (ADDR pin to GND)
    """
    i2c = busio.I2C(SCL, SDA)
    sensor = adafruit_sht31d.SHT31D(i2c)
    return round(sensor.temperature, 2), round(sensor.relative_humidity, 2)