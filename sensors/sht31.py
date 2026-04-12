import board
import busio
import adafruit_sht31d

def get_readings():
    """
    Read temperature and humidity from SHT3x sensor.
    Works with SHT30, SHT31, and SHT35 variants via I2C.
    Default address: 0x44 (ADDR pin to GND)
    """
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_sht31d.SHT31D(i2c)
    return round(sensor.temperature, 2), round(sensor.relative_humidity, 2)