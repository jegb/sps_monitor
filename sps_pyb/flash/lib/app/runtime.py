try:
    import time
except ImportError:
    import utime as time

try:
    from .mqtt_client import MQTTPublisher
    from .payload import PM_FIELDS, build_mqtt_payload, build_sensor_record
    from .storage import StorageManager
    from .time_sync import TimeSync
    from .wifi import WiFiManager
    from ..sensors.aht10 import AHT10Sensor
    from ..sensors.dht11 import DHT11Sensor
    from ..sensors.ppd42 import PPD42Sensor, estimate_mass_concentration_ugm3
    from ..sensors.sht2x import SHT2XSensor
    from ..sensors.sht3x import SHT3XSensor
    from ..sensors.sps30 import SPS30Sensor
except (ImportError, ValueError):
    from app.mqtt_client import MQTTPublisher
    from app.payload import PM_FIELDS, build_mqtt_payload, build_sensor_record
    from app.storage import StorageManager
    from app.time_sync import TimeSync
    from app.wifi import WiFiManager
    from sensors.aht10 import AHT10Sensor
    from sensors.dht11 import DHT11Sensor
    from sensors.ppd42 import PPD42Sensor, estimate_mass_concentration_ugm3
    from sensors.sht2x import SHT2XSensor
    from sensors.sht3x import SHT3XSensor
    from sensors.sps30 import SPS30Sensor


def _sleep_seconds(seconds):
    if seconds <= 0:
        return

    if hasattr(time, "sleep"):
        time.sleep(seconds)
    else:
        time.sleep_ms(int(seconds * 1000))


class PPD42CompatBuffer:
    def __init__(self, fields=PM_FIELDS):
        self.fields = tuple(fields)
        self.values = {field_name: None for field_name in self.fields}
        self.index = 0

    def update(self, particle_count):
        field_name = self.fields[self.index]
        self.values[field_name] = particle_count
        self.index = (self.index + 1) % len(self.fields)
        return dict(self.values), field_name


class PPD42SingleFieldMapper:
    def __init__(
        self,
        field_name,
        *,
        particle_size_um,
        density_kg_m3,
        calibration_factor,
    ):
        self.field_name = field_name
        self.particle_size_um = float(particle_size_um)
        self.density_kg_m3 = float(density_kg_m3)
        self.calibration_factor = float(calibration_factor)

    def update(self, particle_count):
        value = estimate_mass_concentration_ugm3(
            particle_count,
            particle_size_um=self.particle_size_um,
            density_kg_m3=self.density_kg_m3,
            calibration_factor=self.calibration_factor,
        )
        return {self.field_name: value}, self.field_name


class StationRuntime:
    def __init__(self, config):
        self.config = config
        self.publish_interval_s = int(getattr(config, "PUBLISH_INTERVAL_S", 60))
        self.mqtt_enabled = bool(getattr(config, "MQTT_ENABLED", True))
        self.mqtt_topic = getattr(config, "MQTT_TOPIC", "airquality/sensor")
        self.mqtt_calibration_topic = str(getattr(config, "MQTT_CALIBRATION_TOPIC", "")).strip() or None
        self.ppd42_sample_duration_s = int(getattr(config, "PPD42_SAMPLE_DURATION", 30))
        self.mqtt_strict_contract = bool(getattr(config, "MQTT_STRICT_CONTRACT", False))

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

        self.i2c = self._create_i2c() if self._needs_i2c() else None
        self.sps30 = self._create_sps30()
        self.env_sensor = self._create_env_sensor()
        self.ppd42 = self._create_ppd42()
        self.ppd42_compat = self._create_ppd42_compat()

    def _sps30_enabled(self):
        return bool(getattr(self.config, "SPS30_ENABLED", True))

    def _create_i2c(self):
        from machine import I2C

        bus = getattr(self.config, "I2C_BUS", "X")
        freq = int(getattr(self.config, "I2C_FREQ", 100000))

        try:
            return I2C(bus, freq=freq)
        except TypeError:
            return I2C(int(bus), freq=freq)

    def _needs_i2c(self):
        if self._sps30_enabled():
            return True

        return self._env_sensor_kind() in ("sht3x", "sht20", "aht10")

    def _create_sps30(self):
        if not self._sps30_enabled():
            return None

        sensor = SPS30Sensor(
            self.i2c,
            address=int(getattr(self.config, "SPS30_ADDR", 0x69)),
        )
        if not sensor.probe():
            print("runtime: SPS30 not found at 0x%02X" % sensor.address)
        return sensor

    def _ppd42_enabled(self):
        return bool(getattr(self.config, "PPD42_ENABLED", False))

    def _env_sensor_kind(self):
        kind = str(getattr(self.config, "ENV_SENSOR", "")).strip().lower()
        if kind:
            return kind

        if bool(getattr(self.config, "SHT3X_ENABLED", True)):
            return "sht3x"
        return "none"

    def _create_env_sensor(self):
        kind = self._env_sensor_kind()
        if kind in ("", "none", "off"):
            return None

        if kind == "sht3x":
            sensor = SHT3XSensor(
                self.i2c,
                address=int(getattr(self.config, "SHT3X_ADDR", 0x44)),
            )
            if not sensor.probe():
                print("runtime: SHT3x not found at 0x%02X" % sensor.address)
            return sensor

        if kind == "sht20":
            sensor = SHT2XSensor(
                self.i2c,
                address=int(getattr(self.config, "SHT20_ADDR", 0x40)),
            )
            if not sensor.probe():
                print("runtime: SHT20/SHT2x not found at 0x%02X" % sensor.address)
            return sensor

        if kind == "aht10":
            sensor = AHT10Sensor(
                self.i2c,
                address=int(getattr(self.config, "AHT10_ADDR", 0x38)),
            )
            if not sensor.probe():
                print("runtime: AHT10 not found at 0x%02X" % sensor.address)
            return sensor

        if kind == "dht11":
            sensor = DHT11Sensor(
                pin=getattr(self.config, "DHT11_PIN", "X1"),
            )
            if not sensor.probe():
                print("runtime: DHT11 not found on pin %s" % getattr(self.config, "DHT11_PIN", "X1"))
            return sensor

        raise ValueError("Unsupported ENV_SENSOR: %s" % kind)

    def _create_ppd42(self):
        if not self._ppd42_enabled():
            return None

        try:
            return PPD42Sensor(
                pin=getattr(self.config, "PPD42_PIN", "X2"),
                particle_size=float(getattr(self.config, "PPD42_PARTICLE_SIZE", 2.5)),
            )
        except Exception as exc:
            print("runtime: PPD42 init failed:", exc)
            return None

    def _ppd42_compat_mode(self):
        return str(getattr(self.config, "PPD42_COMPAT_MODE", "none")).strip().lower()

    def _create_ppd42_compat(self):
        if self.ppd42 is None:
            return None

        compat_mode = self._ppd42_compat_mode()
        if compat_mode in ("", "none", "off"):
            return None

        if self.sps30 is not None:
            print("runtime: ignoring PPD42 compat mode because SPS30 is enabled")
            return None

        if compat_mode == "hold4_pm_fields":
            if self.publish_interval_s != self.ppd42_sample_duration_s:
                print(
                    "runtime: PPD42 compat mode works best when "
                    "PUBLISH_INTERVAL_S == PPD42_SAMPLE_DURATION"
                )
            return PPD42CompatBuffer()

        if compat_mode == "pm25_mass_estimate":
            return PPD42SingleFieldMapper(
                "pm_2_5",
                particle_size_um=float(getattr(self.config, "PPD42_PARTICLE_SIZE", 2.5)),
                density_kg_m3=float(getattr(self.config, "PPD42_PARTICLE_DENSITY_KG_M3", 1650.0)),
                calibration_factor=float(getattr(self.config, "PPD42_MASS_CALIBRATION_FACTOR", 1.0)),
            )

        raise ValueError("Unsupported PPD42_COMPAT_MODE: %s" % compat_mode)

    def _build_publish_payload(self, record):
        return build_mqtt_payload(
            record,
            include_optional_fields=not self.mqtt_strict_contract,
            drop_null_fields=self.mqtt_strict_contract,
        )

    def _publish_record(self, client, record):
        client.publish(self.mqtt_topic, self._build_publish_payload(record))
        if self.mqtt_calibration_topic and self.mqtt_calibration_topic != self.mqtt_topic:
            client.publish(self.mqtt_calibration_topic, record)

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
                self._publish_record(client, record)
                self.storage.mark_queue_offset(next_offset)
                drained = True

            if drained:
                self.storage.compact_queue()
                print("mqtt: replay queue drained")
        except Exception as exc:
            print("mqtt: replay failed:", exc)
            self.mqtt.reset()

    def _capture_record(self):
        pm_data = None
        if self.sps30 is not None:
            pm_data = self.sps30.read_measurement()
        temp = None
        humidity = None
        pm_fields = None
        ppd42_particle_count = None
        ppd42_particle_size = None

        if self.env_sensor is not None:
            temp, humidity = self.env_sensor.read_temperature_humidity()

        if self.ppd42 is not None:
            reading = self.ppd42.get_reading(
                sample_duration=self.ppd42_sample_duration_s
            )
            ppd42_particle_count = reading.get("particle_count")
            ppd42_particle_size = reading.get("particle_size")
            if self.ppd42_compat is not None:
                pm_fields, updated_field = self.ppd42_compat.update(ppd42_particle_count)
                print("runtime: PPD42 compat updated %s" % updated_field)

        return build_sensor_record(
            self.time_sync.current_timestamp(),
            pm_data,
            temp,
            humidity,
            pm_fields=pm_fields,
            ppd42_particle_count=ppd42_particle_count,
            ppd42_particle_size=ppd42_particle_size,
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
            self._publish_record(client, record)
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
                if self.sps30 is not None:
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
