try:
    import time
except ImportError:
    import utime as time

try:
    import network
except ImportError:
    network = None


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.monotonic() * 1000)


def _ticks_diff(now, then):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now, then)
    return now - then


def _sleep_ms(delay_ms):
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(delay_ms)
    else:
        time.sleep(delay_ms / 1000.0)


class WiFiManager:
    def __init__(self, ssid, password, connect_timeout_s=15):
        self.ssid = ssid
        self.password = password
        self.connect_timeout_s = int(connect_timeout_s)
        self._wlan = None

    def _station_interface_id(self):
        if hasattr(network, "STA_IF"):
            return network.STA_IF
        if hasattr(network, "WLAN") and hasattr(network.WLAN, "IF_STA"):
            return network.WLAN.IF_STA
        raise RuntimeError("station Wi-Fi interface is unavailable")

    def _get_wlan(self):
        if network is None:
            raise RuntimeError("network module is unavailable")

        if self._wlan is None:
            self._wlan = network.WLAN(self._station_interface_id())
            self._wlan.active(True)

        return self._wlan

    def is_configured(self):
        return bool(self.ssid)

    def is_connected(self):
        return self._wlan is not None and self._wlan.isconnected()

    def connect(self, timeout_s=None):
        if not self.is_configured():
            print("wifi: WIFI_SSID is empty; skipping connect")
            return False

        wlan = self._get_wlan()
        if wlan.isconnected():
            return True

        wlan.connect(self.ssid, self.password)
        timeout_ms = int((timeout_s or self.connect_timeout_s) * 1000)
        start_ms = _ticks_ms()

        while not wlan.isconnected() and _ticks_diff(_ticks_ms(), start_ms) < timeout_ms:
            _sleep_ms(200)

        if wlan.isconnected():
            print("wifi: connected:", wlan.ifconfig()[0])
            return True

        print("wifi: connection timed out")
        return False

    def ensure_connected(self):
        if self.is_connected():
            return True
        return self.connect()

    def ifconfig(self):
        wlan = self._get_wlan()
        if not wlan.isconnected():
            return None
        return wlan.ifconfig()
