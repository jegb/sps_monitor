import time
import sys
# Import board FIRST to ensure adafruit_dht gets the right one
from adafruit_blinka.board.raspberrypi import raspi_40pin
sys.modules['board'] = raspi_40pin

import adafruit_dht
from adafruit_blinka.board.raspberrypi.raspi_40pin import D4

# Initialize the DHT device, with data pin connected to GPIO4
dht_device = adafruit_dht.DHT11(D4)

def read():
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        return temperature_c, humidity
    except RuntimeError as error:
        print(f"Reading from DHT sensor failed: {error.args[0]}")
        return None, None