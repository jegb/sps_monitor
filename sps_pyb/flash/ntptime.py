try:
    import socket
except ImportError:
    import usocket as socket

try:
    import struct
except ImportError:
    import ustruct as struct

try:
    import time as _time
except ImportError:
    import utime as _time

host = "pool.ntp.org"
NTP_DELTA_1970 = 2208988800
NTP_DELTA_2000 = 3155673600
_QUERY = bytearray(48)
_QUERY[0] = 0x1B


def _ntp_delta():
    epoch_year = _time.gmtime(0)[0]
    if epoch_year == 2000:
        return NTP_DELTA_2000
    return NTP_DELTA_1970


def _rtc_datetime_tuple(timestamp):
    tm = _time.gmtime(timestamp)
    return (
        tm[0],
        tm[1],
        tm[2],
        tm[6] + 1,
        tm[3],
        tm[4],
        tm[5],
        0,
    )


def time():
    address = socket.getaddrinfo(host, 123)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        if hasattr(sock, "settimeout"):
            sock.settimeout(1)
        sock.sendto(_QUERY, address)
        message = sock.recv(48)
    finally:
        sock.close()

    return struct.unpack("!I", message[40:44])[0] - _ntp_delta()


def settime():
    timestamp = time()
    rtc_value = _rtc_datetime_tuple(timestamp)

    try:
        from machine import RTC

        RTC().datetime(rtc_value)
        return timestamp
    except Exception:
        pass

    try:
        from pyb import RTC

        RTC().datetime(rtc_value)
        return timestamp
    except Exception:
        pass

    raise RuntimeError("RTC interface unavailable")
