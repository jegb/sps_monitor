import sys

try:
    import time
except ImportError:
    import utime as time


def _add_lib_path(path):
    if path not in sys.path:
        sys.path.append(path)


_add_lib_path("/flash/lib")
_add_lib_path("lib")

try:
    import config
except ImportError as exc:
    raise SystemExit("Missing config.py on the board filesystem") from exc

try:
    from app.mqtt_client import MQTTPublisher
    from app.wifi import WiFiManager
except ImportError:
    from sps_pyb.flash.lib.app.mqtt_client import MQTTPublisher
    from sps_pyb.flash.lib.app.wifi import WiFiManager


def build_mock_payload(sequence):
    sequence = int(sequence)
    phase = sequence % 12
    return {
        "pm_1_0": round(1.0 + 0.2 * phase, 1),
        "pm_2_5": round(2.0 + 0.5 * phase, 1),
        "pm_4_0": round(3.5 + 0.7 * phase, 1),
        "pm_10_0": round(5.0 + 0.9 * phase, 1),
        "temp": round(24.0 + 0.4 * (phase % 5), 1),
        "humidity": round(45.0 + 1.3 * (phase % 7), 1),
    }


def run_once(sequence=0):
    wifi = WiFiManager(
        getattr(config, "WIFI_SSID", ""),
        getattr(config, "WIFI_PASSWORD", ""),
    )
    if not wifi.ensure_connected():
        raise RuntimeError("mock: Wi-Fi connect failed")

    ifconfig = wifi.ifconfig()
    if ifconfig is not None:
        print("mock: wifi ifconfig:", ifconfig)

    client = MQTTPublisher(
        host=getattr(config, "MQTT_HOST", ""),
        port=int(getattr(config, "MQTT_PORT", 1883)),
        client_id=getattr(config, "MQTT_CLIENT_ID", None),
    )
    client.connect(clean_session=True)

    payload = build_mock_payload(sequence)
    topic = getattr(config, "MQTT_TOPIC", "airquality/sensor")
    print("mock: publishing to %s -> %s" % (topic, payload))
    client.publish(topic, payload)
    client.disconnect()
    return payload


def run():
    wifi = WiFiManager(
        getattr(config, "WIFI_SSID", ""),
        getattr(config, "WIFI_PASSWORD", ""),
    )
    if not wifi.ensure_connected():
        raise RuntimeError("mock: Wi-Fi connect failed")

    ifconfig = wifi.ifconfig()
    if ifconfig is not None:
        print("mock: wifi ifconfig:", ifconfig)

    client = MQTTPublisher(
        host=getattr(config, "MQTT_HOST", ""),
        port=int(getattr(config, "MQTT_PORT", 1883)),
        client_id=getattr(config, "MQTT_CLIENT_ID", None),
    )
    client.connect(clean_session=True)

    interval_s = int(getattr(config, "MOCK_PUBLISH_INTERVAL_S", 5))
    publish_count = int(getattr(config, "MOCK_PUBLISH_COUNT", 0))
    topic = getattr(config, "MQTT_TOPIC", "airquality/sensor")

    sequence = 0
    try:
        while True:
            payload = build_mock_payload(sequence)
            print("mock: publishing to %s -> %s" % (topic, payload))
            client.publish(topic, payload)
            sequence += 1

            if publish_count and sequence >= publish_count:
                break

            time.sleep(interval_s)
    finally:
        client.disconnect()


if __name__ == "__main__":
    run()
