import time
import board
import adafruit_dht

# Initialize the DHT device, with data pin connected to GPIO4
dht_device = adafruit_dht.DHT11(board.D4)

def read():
    try:
        temperature_c = dht_device.temperature
        humidity = dht_device.humidity
        return temperature_c, humidity
    except RuntimeError as error:
        print(f"Reading from DHT sensor failed: {error.args[0]}")
        return None, None