try:
    import socket
except ImportError:
    import usocket as socket

try:
    import select
except ImportError:
    try:
        import uselect as select
    except ImportError:
        select = None

try:
    import struct
except ImportError:
    import ustruct as struct

try:
    import time
except ImportError:
    import utime as time

try:
    import errno
except ImportError:
    try:
        import uerrno as errno
    except ImportError:
        errno = None


class MQTTException(Exception):
    pass


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


def _errno_value(name, fallback):
    if errno is not None and hasattr(errno, name):
        return getattr(errno, name)
    return fallback


_ERRNO_IN_PROGRESS = frozenset(
    (
        _errno_value("EINPROGRESS", 115),
        _errno_value("EALREADY", 114),
        _errno_value("EWOULDBLOCK", 11),
        115,
        114,
        11,
    )
)

_ERRNO_IS_CONNECTED = frozenset((_errno_value("EISCONN", 106), 106, 56))


def _socket_errno(exc):
    if hasattr(exc, "errno") and exc.errno is not None:
        return exc.errno
    if exc.args:
        first = exc.args[0]
        if isinstance(first, int):
            return first
    return None


def _as_bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return str(value).encode("utf-8")


def _pack_string(value):
    data = _as_bytes(value)
    return struct.pack("!H", len(data)) + data


def _encode_remaining_length(length):
    encoded = bytearray()
    while True:
        digit = length & 0x7F
        length >>= 7
        if length:
            digit |= 0x80
        encoded.append(digit)
        if not length:
            break
    return bytes(encoded)


def _recv_exact(sock, size):
    chunks = bytearray()
    while len(chunks) < size:
        data = sock.recv(size - len(chunks))
        if not data:
            raise OSError("socket closed")
        chunks.extend(data)
    return bytes(chunks)


def _send_all(sock, payload):
    remaining = payload
    while remaining:
        sent = sock.send(remaining)
        if sent <= 0:
            raise OSError("socket send failed")
        remaining = remaining[sent:]


def _wait_for_connect(sock, sockaddr, timeout_ms):
    start_ms = _ticks_ms()
    while _ticks_diff(_ticks_ms(), start_ms) < timeout_ms:
        try:
            if select is not None and hasattr(select, "poll"):
                poller = select.poll()
                eventmask = 0
                for name in ("POLLOUT", "POLLERR", "POLLHUP"):
                    if hasattr(select, name):
                        eventmask |= getattr(select, name)
                poller.register(sock, eventmask or 0)
                poller.poll(100)
            else:
                _sleep_ms(100)

            sock.connect(sockaddr)
            return
        except OSError as exc:
            code = _socket_errno(exc)
            if code in _ERRNO_IS_CONNECTED:
                return
            if code in _ERRNO_IN_PROGRESS:
                continue
            raise
    raise OSError("socket connect timed out")


class MQTTClient:
    def __init__(self, client_id, server, port=1883, keepalive=60):
        self.client_id = _as_bytes(client_id)
        self.server = server
        self.port = int(port)
        self.keepalive = int(keepalive)
        self.sock = None

    def connect(self, clean_session=True):
        self.disconnect()

        addrinfo = socket.getaddrinfo(self.server, self.port, 0, socket.SOCK_STREAM)[0]
        family, socktype, proto, _, sockaddr = addrinfo
        sock = socket.socket(family, socktype, proto)
        timeout_s = 5
        if hasattr(sock, "settimeout"):
            sock.settimeout(timeout_s)
        try:
            sock.connect(sockaddr)
        except OSError as exc:
            if _socket_errno(exc) not in _ERRNO_IN_PROGRESS:
                sock.close()
                raise
            _wait_for_connect(sock, sockaddr, timeout_s * 1000)

        connect_flags = 0x02 if clean_session else 0x00
        variable_header = b"\x00\x04MQTT\x04" + bytes((connect_flags,)) + struct.pack(
            "!H", self.keepalive
        )
        payload = _pack_string(self.client_id)
        packet = (
            b"\x10"
            + _encode_remaining_length(len(variable_header) + len(payload))
            + variable_header
            + payload
        )
        _send_all(sock, packet)

        response = _recv_exact(sock, 4)
        if response[0] != 0x20 or response[1] != 0x02:
            sock.close()
            raise MQTTException("invalid CONNACK from broker")
        if response[3] != 0x00:
            sock.close()
            raise MQTTException("broker rejected connection: %s" % response[3])

        self.sock = sock
        return bool(response[2] & 0x01)

    def publish(self, topic, msg, retain=False, qos=0):
        if qos != 0:
            raise NotImplementedError("Only QoS 0 is supported")
        if self.sock is None:
            raise OSError("MQTT client is not connected")

        header = 0x30 | (0x01 if retain else 0x00)
        variable_header = _pack_string(topic)
        payload = _as_bytes(msg)
        packet = (
            bytes((header,))
            + _encode_remaining_length(len(variable_header) + len(payload))
            + variable_header
            + payload
        )
        _send_all(self.sock, packet)
        return True

    def ping(self):
        if self.sock is None:
            raise OSError("MQTT client is not connected")
        _send_all(self.sock, b"\xC0\x00")

    def disconnect(self):
        if self.sock is None:
            return

        try:
            _send_all(self.sock, b"\xE0\x00")
        except OSError:
            pass

        try:
            self.sock.close()
        except OSError:
            pass

        self.sock = None
