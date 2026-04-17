try:
    import time
except ImportError:
    import utime as time

try:
    from .mqtt_client import MQTTPublisher
    from .payload import build_live_payload, build_sensor_record
    from .storage import StorageManager
    from .time_sync import TimeSync
    from .wifi import WiFiManager
    from ..sensors.sht3x import SHT3XSensor
    from ..sensors.sps30 import SPS30Sensor
except ImportError:
    from app.mqtt_client import MQTTPublisher
    from app.payload import build_live_payload, build_sensor_record
    from app.storage import StorageManager
    from app.time_sync import TimeSync
    from app.wifi import WiFiManager
    from sensors.sht3x import SHT3XSensor
    from sensors.sps30 import SPS30Sensor


def _sleep_seconds(seconds):
    if seconds <= 0:
        return

    if hasattr(time, "sleep"):
        time.sleep(seconds)
    else:
        time.sleep_ms(int(seconds * 1000))


class StationRuntime:
    def __init__(self, config):
        self.config = config
        self.publish_interval_s = int(getattr(config, "PUBLISH_INTERVAL_S", 60))
        self.mqtt_enabled = bool(getattr(config, "MQTT_ENABLED", True))
        self.mqtt_topic = getattr(config, "MQTT_TOPIC", "airquality/sensor")

        self.wifi = WiFiManager(
            getattr(config, "WIFI_SSID", ""),
            getattr(config, "WIFI_PASSWORD", ""),
        )
        self.time_sync = TimeSync(
            enabled=bool(getattr(config, "NTP_ENABLED", True)),
            host=getattr(config, "NTP_HOST", "pool.ntp.org"),
        )
        self.storage = StorageManager(
            root="/sd",
            history_enabled=bool(getattr(config, "SD_HISTORY_ENABLED", True)),
        )
        self.storage.prepare()

        self.mqtt = None
        if self.mqtt_enabled:
            self.mqtt = MQTTPublisher(
                host=getattr(config, "MQTT_HOST", ""),
                port=int(getattr(config, "MQTT_PORT", 1883)),
                client_id=getattr(config, "MQTT_CLIENT_ID", None),
            )

        self.i2c = self._create_i2c()
        self.sps30 = SPS30Sensor(
            self.i2c,
            address=int(getattr(config, "SPS30_ADDR", 0x69)),
        )
        if not self.sps30.probe():
            print("runtime: SPS30 not found at 0x%02X" % self.sps30.address)

        self.sht3x = None
        if bool(getattr(config, "SHT3X_ENABLED", True)):
            self.sht3x = SHT3XSensor(
                self.i2c,
                address=int(getattr(config, "SHT3X_ADDR", 0x44)),
            )
            if not self.sht3x.probe():
                print("runtime: SHT3x not found at 0x%02X" % self.sht3x.address)

    def _create_i2c(self):
        from machine import I2C

        bus = getattr(self.config, "I2C_BUS", "X")
        freq = int(getattr(self.config, "I2C_FREQ", 100000))

        try:
            return I2C(bus, freq=freq)
        except TypeError:
            return I2C(int(bus), freq=freq)

    def _ensure_mqtt(self):
        if not self.mqtt_enabled or self.mqtt is None:
            return None

        if not self.wifi.ensure_connected():
            return None

        if self.mqtt.is_connected():
            return self.mqtt

        try:
            self.mqtt.connect()
            return self.mqtt
        except Exception as exc:
            print("mqtt: connect failed:", exc)
            self.mqtt.reset()
            return None

    def _replay_pending(self):
        if not self.storage.has_durable_storage():
            return

        client = self._ensure_mqtt()
        if client is None:
            return

        try:
            drained = False
            for _, next_offset, record in self.storage.iter_pending():
                client.publish(self.mqtt_topic, build_live_payload(record))
                self.storage.mark_queue_offset(next_offset)
                drained = True

            if drained:
                self.storage.compact_queue()
                print("mqtt: replay queue drained")
        except Exception as exc:
            print("mqtt: replay failed:", exc)
            self.mqtt.reset()

    def _capture_record(self):
        pm_data = self.sps30.read_measurement()
        temp = None
        humidity = None

        if self.sht3x is not None:
            temp, humidity = self.sht3x.read_temperature_humidity()

        return build_sensor_record(
            self.time_sync.current_timestamp(),
            pm_data,
            temp,
            humidity,
        )

    def _persist_history(self, record):
        if not self.storage.append_history(record):
            if self.storage.history_enabled:
                print("storage: history disabled because /sd is unavailable")

    def _queue_record(self, record):
        if self.storage.append_queue(record):
            print("mqtt: queued sample for replay")
            return
        print("mqtt: publish failed and /sd is unavailable; dropping sample")

    def run_once(self):
        if self.wifi.is_configured():
            self.wifi.ensure_connected()
        self.time_sync.maybe_sync()
        self._replay_pending()

        record = self._capture_record()
        self._persist_history(record)

        if not self.mqtt_enabled:
            return record

        client = self._ensure_mqtt()
        if client is None:
            self._queue_record(record)
            return record

        try:
            client.publish(self.mqtt_topic, build_live_payload(record))
            print("mqtt: published live sample")
        except Exception as exc:
            print("mqtt: publish failed:", exc)
            self.mqtt.reset()
            self._queue_record(record)

        return record

    def run_forever(self):
        self.time_sync.maybe_sync(force=True)

        while True:
            start = time.time()
            try:
                self.run_once()
            except Exception as exc:
                print("runtime: sample loop failed:", exc)
                try:
                    self.sps30.stop_measurement()
                except Exception:
                    pass

            elapsed = time.time() - start
            remaining = self.publish_interval_s - elapsed
            if remaining > 0:
                _sleep_seconds(remaining)


def run_forever(config):
    StationRuntime(config).run_forever()
