try:
    import time
except ImportError:
    import utime as time

try:
    import ntptime
except ImportError:
    ntptime = None


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.monotonic() * 1000)


def _ticks_diff(now, then):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now, then)
    return now - then


def format_utc_timestamp(now):
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
        now[0],
        now[1],
        now[2],
        now[3],
        now[4],
        now[5],
    )


class TimeSync:
    def __init__(self, enabled=True, host="pool.ntp.org", sync_interval_s=21600):
        self.enabled = enabled
        self.host = host
        self.sync_interval_s = int(sync_interval_s)
        self._last_sync_ms = None

    def current_timestamp(self):
        return format_utc_timestamp(time.gmtime())

    def sync(self):
        if not self.enabled or ntptime is None:
            return False

        ntptime.host = self.host
        ntptime.settime()
        self._last_sync_ms = _ticks_ms()
        print("ntp: clock synchronized")
        return True

    def maybe_sync(self, force=False):
        if not self.enabled:
            return False

        should_sync = force or self._last_sync_ms is None
        if not should_sync:
            elapsed_ms = _ticks_diff(_ticks_ms(), self._last_sync_ms)
            should_sync = elapsed_ms >= (self.sync_interval_s * 1000)

        if not should_sync:
            return False

        try:
            return self.sync()
        except Exception as exc:
            print("ntp: sync failed:", exc)
            return False
