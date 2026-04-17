from datetime import datetime, timezone
import logging
from pathlib import Path
import time

from .mqtt_client import MQTTPublisher
from .payload import build_live_payload, build_sensor_record
from .storage import StorageManager
from ..sensors.sht3x import SHT3XSensor
from ..sensors.sps30 import SPS30Sensor

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class StationRuntime:
    def __init__(self, config):
        self.config = config
        self.publish_interval_s = int(getattr(config, "PUBLISH_INTERVAL_S", 60))
        self.mqtt_enabled = bool(getattr(config, "MQTT_ENABLED", True))
        self.mqtt_topic = getattr(config, "MQTT_TOPIC", "airquality/sensor")

        data_dir = getattr(config, "DATA_DIR", "") or str(DEFAULT_DATA_DIR)
        self.storage = StorageManager(
            root=data_dir,
            history_enabled=bool(getattr(config, "HISTORY_ENABLED", True)),
        )
        self.storage.prepare()

        self.mqtt = None
        if self.mqtt_enabled:
            self.mqtt = MQTTPublisher(
                host=getattr(config, "MQTT_HOST", ""),
                port=int(getattr(config, "MQTT_PORT", 1883)),
                client_id=getattr(config, "MQTT_CLIENT_ID", None),
            )

        self.sps30 = SPS30Sensor(
            bus_num=int(getattr(config, "I2C_BUS", 1)),
            address=int(getattr(config, "SPS30_ADDR", 0x69)),
        )
        if not self.sps30.probe():
            logging.warning("SPS30 not detected at 0x%02X", self.sps30.address)

        self.sht3x = None
        if bool(getattr(config, "SHT3X_ENABLED", True)):
            sensor = SHT3XSensor(
                bus_num=int(getattr(config, "I2C_BUS", 1)),
                address=int(getattr(config, "SHT3X_ADDR", 0x44)),
            )
            if not sensor.probe():
                logging.warning("SHT3x not detected at 0x%02X", sensor.address)
            else:
                self.sht3x = sensor

    def _replay_pending(self):
        if not self.mqtt_enabled or self.mqtt is None:
            return

        drained = False
        try:
            for _, next_offset, record in self.storage.iter_pending():
                self.mqtt.publish(self.mqtt_topic, build_live_payload(record))
                self.storage.mark_queue_offset(next_offset)
                drained = True
        except Exception as exc:
            logging.warning("Replay failed: %s", exc)
            return

        if drained:
            self.storage.compact_queue()
            logging.info("Replay queue drained")

    def _capture_record(self):
        pm_data = self.sps30.read_measurement()
        temp = None
        humidity = None
        if self.sht3x is not None:
            try:
                temp, humidity = self.sht3x.read_temperature_humidity()
            except Exception as exc:
                logging.warning("SHT3x read failed: %s", exc)

        return build_sensor_record(_utc_timestamp(), pm_data, temp, humidity)

    def _queue_record(self, record):
        self.storage.append_queue(record)
        logging.warning("Sample queued for later replay")

    def run_once(self):
        self._replay_pending()
        record = self._capture_record()
        self.storage.append_history(record)

        if not self.mqtt_enabled or self.mqtt is None:
            return record

        try:
            self.mqtt.publish(self.mqtt_topic, build_live_payload(record))
            logging.info("Published MQTT sample")
        except Exception as exc:
            logging.warning("Live publish failed: %s", exc)
            self._queue_record(record)

        return record

    def run_forever(self):
        while True:
            started = time.monotonic()
            try:
                self.run_once()
            except Exception as exc:
                logging.exception("Sample loop failed: %s", exc)
                try:
                    self.sps30.stop_measurement()
                except Exception:
                    pass

            elapsed = time.monotonic() - started
            delay = self.publish_interval_s - elapsed
            if delay > 0:
                time.sleep(delay)


def run_forever(config):
    logging.basicConfig(
        level=getattr(logging, str(getattr(config, "LOG_LEVEL", "INFO")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    StationRuntime(config).run_forever()
