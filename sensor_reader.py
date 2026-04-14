import time
import logging
import sqlite3
import paho.mqtt.publish as publish
import random
from board_detect import init_board

# Initialize board BEFORE any adafruit imports
board_module, board_name = init_board()

from config import SENSOR_TYPE, EMULATE, PPD42_ENABLED, PPD42_PIN, PPD42_PARTICLE_SIZE, PPD42_SAMPLE_DURATION
if SENSOR_TYPE in ("SHT31", "SHT3X"):
    from sensors import sht31 as temp_sensor
elif SENSOR_TYPE == "DHT11":
    from sensors import dht11 as temp_sensor
else:
    raise ValueError(f"Unsupported sensor: {SENSOR_TYPE}")

try:
    # Try pure Python I2C driver first (works on all RPi models)
    from sensors.sps30_i2c import read_sps30
    logging.info("Using pure Python SPS30 I2C driver")
except ImportError:
    # Fallback to C library if Python driver not available
    from c_sps30_i2c.sps30_ctypes_wrapper import read_sps30
    logging.info("Using C library SPS30 driver")

def is_sps30_available():
    """Check if SPS30 is present on I2C bus (address 0x69)."""
    try:
        import busio
        from board import SCL, SDA
        i2c = busio.I2C(SCL, SDA)

        while not i2c.try_lock():
            pass

        try:
            i2c.writeto(0x69, b'')
            return True
        except OSError:
            # Device not responding at 0x69
            return False
        finally:
            i2c.unlock()
            i2c.deinit()
    except Exception as e:
        logging.warning(f"Error checking SPS30 availability: {e}")
        return False

if PPD42_ENABLED:
    from sensors.ppd42 import PPD42Sensor
    ppd42_sensor = PPD42Sensor(pin=PPD42_PIN, particle_size=PPD42_PARTICLE_SIZE)
else:
    ppd42_sensor = None

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

def store_to_db(pm_data, temp, humidity, particle_count=None, particle_size=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Store as UTC - browser will convert to local time
    c.execute("""
        INSERT INTO sps30_data (timestamp, pm1, pm25, pm4, pm10, temp, humidity, particle_count, particle_size)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pm_data.mc_1p0, pm_data.mc_2p5, pm_data.mc_4p0, pm_data.mc_10p0,
        temp, humidity, particle_count, particle_size
    ))
    conn.commit()
    conn.close()

def publish_to_mqtt(pm_data, temp, humidity, particle_count=None, particle_size=None):
    payload = {
        "pm_1_0": round(pm_data.mc_1p0, 1),
        "pm_2_5": round(pm_data.mc_2p5, 1),
        "pm_4_0": round(pm_data.mc_4p0, 1),
        "pm_10_0": round(pm_data.mc_10p0, 1),
        "temp": round(temp, 1),
        "humidity": round(humidity, 1),
    }
    if particle_count is not None and particle_size is not None:
        payload["ppd42_particle_count"] = round(particle_count, 2)
        payload["ppd42_particle_size"] = particle_size
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

    # Try to connect to MQTT broker, but don't fail if unavailable
    client = None
    try:
        client = mqtt.Client()
        client.on_message = lambda c, u, m: on_control(c, u, m)
        client.connect(MQTT_BROKER)
        client.subscribe("airquality/control/logging")
        client.loop_start()
        logging.info(f"Connected to MQTT broker at {MQTT_BROKER}")
    except Exception as e:
        logging.warning(f"MQTT broker unavailable ({MQTT_BROKER}): {e}. Continuing without MQTT.")

    # Check SPS30 availability at startup
    sps30_available = is_sps30_available()
    if not sps30_available:
        logging.warning("SPS30 not detected on I2C bus. PM readings will be skipped.")

    while True:
        print(f"[LOOP] Starting iteration...", flush=True)
        particle_count = None
        particle_size = None
        pm_data = None

        if EMULATE:
            fake = generate_fake_readings()
            pm_data = FakeMeasurement(fake)
            temp = fake["temp"]
            humidity = fake["humidity"]
        else:
            if sps30_available:
                try:
                    print(f"[SPS30] Reading...", flush=True)
                    pm_data = read_sps30()
                    print(f"[SPS30] Success: PM2.5={pm_data.mc_2p5}, PM10={pm_data.mc_10p0}", flush=True)
                    logging.info(f"PM2.5: {pm_data.mc_2p5}, PM10: {pm_data.mc_10p0}")
                except Exception as e:
                    print(f"[SPS30] Failed: {e}", flush=True)
                    logging.warning(f"SPS30 read failed: {e}")
                    pm_data = None

            print(f"[TEMP] Reading...", flush=True)
            temp, humidity = temp_sensor.get_readings()
            print(f"[TEMP] Success: {temp}°C, {humidity}%", flush=True)
            logging.info(f"Temp: {temp}°C, Humidity: {humidity}%")

            if ppd42_sensor:
                ppd42_reading = ppd42_sensor.get_reading(sample_duration=PPD42_SAMPLE_DURATION)
                if ppd42_reading:
                    particle_count = ppd42_reading.get("particle_count")
                    particle_size = ppd42_reading.get("particle_size")
                    logging.info(f"PPD42 (PM{particle_size}): {particle_count} pcs/0.01cf")

        print(f"[STORE] logging_enabled={logging_enabled}, pm_data={pm_data is not None}", flush=True)
        if logging_enabled and pm_data:
            print(f"[STORE] Writing to DB...", flush=True)
            store_to_db(pm_data, temp, humidity, particle_count, particle_size)
            print(f"[STORE] DB write complete", flush=True)
            if client:
                try:
                    publish_to_mqtt(pm_data, temp, humidity, particle_count, particle_size)
                except Exception as e:
                    logging.debug(f"Failed to publish to MQTT: {e}")
        else:
            print(f"[STORE] Skipped (logging_enabled={logging_enabled}, pm_data={pm_data})", flush=True)

        print(f"[LOOP] Sleeping 60s...", flush=True)
        time.sleep(60)

if __name__ == "__main__":
    main()
