import time
import logging
import sqlite3
import paho.mqtt.publish as publish
import random
from config import SENSOR_TYPE, EMULATE
if SENSOR_TYPE == "SHT31":
    from sensors import sht31 as temp_sensor
elif SENSOR_TYPE == "DHT11":
    from sensors import dht11 as temp_sensor
else:
    raise ValueError("Unsupported sensor")

from c_sps30_i2c.sps30_ctypes_wrapper import read_sps30

logging.basicConfig(level=logging.INFO)

logging_enabled = True

class FakeMeasurement:
    def __init__(self, f):
        self.mc_1p0 = f["mc_1p0"]
        self.mc_2p5 = f["mc_2p5"]
        self.mc_4p0 = f["mc_4p0"]
        self.mc_10p0 = f["mc_10p0"]
        self.typical_particle_size = f["typical_particle_size"]

DB_FILE = "sps30_data.db"
MQTT_BROKER = "localhost"
MQTT_TOPIC = "airquality/sensor"

def generate_fake_readings():
    return {
        "mc_1p0": round(random.uniform(0.5, 10.0), 1),
        "mc_2p5": round(random.uniform(1.0, 25.0), 1),
        "mc_4p0": round(random.uniform(1.5, 35.0), 1),
        "mc_10p0": round(random.uniform(2.0, 50.0), 1),
        "typical_particle_size": round(random.uniform(0.3, 1.2), 2),
        "temp": round(random.uniform(20, 30), 1),
        "humidity": round(random.uniform(30, 70), 1)
    }

def store_to_db(pm_data, temp, humidity):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sensor_data (timestamp, pm_1_0, pm_2_5, pm_4_0, pm_10_0, temp, humidity)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
    """, (
        pm_data.mc_1p0, pm_data.mc_2p5, pm_data.mc_4p0, pm_data.mc_10p0,
        temp, humidity
    ))
    conn.commit()
    conn.close()

def publish_to_mqtt(pm_data, temp, humidity):
    payload = {
        "pm_1_0": round(pm_data.mc_1p0, 1),
        "pm_2_5": round(pm_data.mc_2p5, 1),
        "pm_4_0": round(pm_data.mc_4p0, 1),
        "pm_10_0": round(pm_data.mc_10p0, 1),
        "temp": round(temp, 1),
        "humidity": round(humidity, 1),
    }
    publish.single(MQTT_TOPIC, str(payload), hostname=MQTT_BROKER)

def main():
    import paho.mqtt.client as mqtt

    def on_control(client, userdata, msg):
        global logging_enabled
        if msg.topic == "airquality/control/logging":
            if msg.payload.decode() == "ON":
                logging_enabled = True
                logging.info("Logging enabled via MQTT.")
            elif msg.payload.decode() == "OFF":
                logging_enabled = False
                logging.info("Logging disabled via MQTT.")

    client = mqtt.Client()
    client.on_message = lambda c, u, m: on_control(c, u, m)
    client.connect(MQTT_BROKER)
    client.subscribe("airquality/control/logging")
    client.loop_start()

    while True:
        if EMULATE:
            fake = generate_fake_readings()
            pm_data = FakeMeasurement(fake)
            temp = fake["temp"]
            humidity = fake["humidity"]
        else:
            pm_data = read_sps30()
            logging.info(f"PM2.5: {pm_data.mc_2p5}, PM10: {pm_data.mc_10p0}")
            temp, humidity = temp_sensor.get_readings()
            logging.info(f"Temp: {temp}°C, Humidity: {humidity}%")

        if logging_enabled:
            store_to_db(pm_data, temp, humidity)
            publish_to_mqtt(pm_data, temp, humidity)

        time.sleep(60)

if __name__ == "__main__":
    main()
