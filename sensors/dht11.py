import Adafruit_DHT
from config import DHT11_PIN

def get_readings():
    sensor = Adafruit_DHT.DHT11
    humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT11_PIN)
    return round(temperature, 2), round(humidity, 2)