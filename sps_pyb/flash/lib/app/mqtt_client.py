try:
    import binascii
except ImportError:
    import ubinascii as binascii

try:
    from machine import unique_id
except ImportError:
    unique_id = None

try:
    from .payload import dumps_json
except ImportError:
    from app.payload import dumps_json

try:
    from ..umqtt.simple import MQTTClient
except (ImportError, ValueError):
    from umqtt.simple import MQTTClient


class MQTTPublisher:
    def __init__(self, host, port=1883, client_id=None, keepalive_s=60):
        self.host = host
        self.port = int(port)
        self.client_id = client_id or self._default_client_id()
        self.keepalive_s = int(keepalive_s)
        self._client = None
        self._connected = False

    def _default_client_id(self):
        if unique_id is None:
            return "sps-pybd"
        return "sps-pybd-" + binascii.hexlify(unique_id()).decode("ascii")

    def is_connected(self):
        return self._connected

    def connect(self, clean_session=True):
        if not self.host:
            raise ValueError("MQTT host is required")

        if self._client is None:
            self._client = MQTTClient(
                client_id=self.client_id,
                server=self.host,
                port=self.port,
                keepalive=self.keepalive_s,
            )

        self._client.connect(clean_session=clean_session)
        self._connected = True
        print("mqtt: connected to %s:%s" % (self.host, self.port))
        return True

    def publish(self, topic, payload, retain=False):
        if not self._connected:
            self.connect()

        message = dumps_json(payload)
        if not isinstance(message, (bytes, bytearray)):
            message = message.encode("utf-8")

        try:
            self._client.publish(topic, message, retain=retain, qos=0)
            return True
        except Exception:
            self.reset()
            raise

    def disconnect(self):
        if self._client is None:
            return

        try:
            self._client.disconnect()
        finally:
            self._connected = False

    def reset(self):
        try:
            self.disconnect()
        finally:
            self._client = None
