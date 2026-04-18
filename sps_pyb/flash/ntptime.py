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
DEFAULT_TIMEOUT_S = 5
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


def _host_candidates(value):
    if value is None:
        value = host

    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value)
    return [item.strip() for item in text.split(",") if item.strip()]


def _recv_message(sock, size):
    if hasattr(sock, "recvfrom"):
        return sock.recvfrom(size)[0]
    return sock.recv(size)


def time(host_override=None, timeout_s=DEFAULT_TIMEOUT_S):
    last_error = None

    for candidate in _host_candidates(host_override):
        try:
            addresses = socket.getaddrinfo(candidate, 123)
        except Exception as exc:
            last_error = exc
            continue

        for entry in addresses:
            family, _socktype, proto, _, address = entry
            sock = socket.socket(family, socket.SOCK_DGRAM, proto)
            try:
                if hasattr(sock, "settimeout"):
                    sock.settimeout(timeout_s)
                if hasattr(sock, "connect"):
                    sock.connect(address)
                    sock.send(_QUERY)
                    message = sock.recv(48)
                else:
                    sock.sendto(_QUERY, address)
                    message = _recv_message(sock, 48)
                if len(message) < 48:
                    raise OSError("short NTP reply")
                return struct.unpack("!I", message[40:44])[0] - _ntp_delta()
            except Exception as exc:
                last_error = exc
            finally:
                sock.close()

    if last_error is None:
        raise OSError("no NTP hosts configured")
    raise last_error


def settime(host_override=None, timeout_s=DEFAULT_TIMEOUT_S):
    timestamp = time(host_override=host_override, timeout_s=timeout_s)
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
