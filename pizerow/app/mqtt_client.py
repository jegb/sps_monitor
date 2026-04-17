try:
    from paho.mqtt import publish as mqtt_publish
except ImportError:
    mqtt_publish = None

from .payload import dumps_json


class MQTTPublisher:
    def __init__(self, host, port=1883, client_id=None, keepalive_s=60):
        self.host = host
        self.port = int(port)
        self.client_id = client_id
        self.keepalive_s = int(keepalive_s)

    def publish(self, topic, payload):
        if mqtt_publish is None:
            raise RuntimeError("paho-mqtt is not installed")
        if not self.host:
            raise ValueError("MQTT host is required")

        mqtt_publish.single(
            topic,
            dumps_json(payload),
            hostname=self.host,
            port=self.port,
            client_id=self.client_id,
            keepalive=self.keepalive_s,
        )
        return True
