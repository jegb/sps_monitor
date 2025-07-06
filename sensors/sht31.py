import board
import busio
import adafruit_sht31d

def get_readings():
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_sht31d.SHT31D(i2c)
    return round(sensor.temperature, 2), round(sensor.relative_humidity, 2)