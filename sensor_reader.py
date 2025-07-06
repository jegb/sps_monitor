import time
import logging
import sqlite3
import paho.mqtt.publish as publish
from config import SENSOR_TYPE
if SENSOR_TYPE == "SHT31":
    from sensors import sht31 as temp_sensor
elif SENSOR_TYPE == "DHT11":
    from sensors import dht11 as temp_sensor
else:
    raise ValueError("Unsupported sensor")

from c_sps30_i2c.sps30_ctypes_wrapper import read_sps30

logging.basicConfig(level=logging.INFO)

DB_FILE = "sps30_data.db"
MQTT_BROKER = "localhost"
MQTT_TOPIC = "airquality/sensor"

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
    while True:
        pm_data = read_sps30()
        logging.info(f"PM2.5: {pm_data.mc_2p5}, PM10: {pm_data.mc_10p0}")
        temp, humidity = temp_sensor.get_readings()
        logging.info(f"Temp: {temp}°C, Humidity: {humidity}%")

        store_to_db(pm_data, temp, humidity)
        publish_to_mqtt(pm_data, temp, humidity)

        time.sleep(60)

if __name__ == "__main__":
    main()
