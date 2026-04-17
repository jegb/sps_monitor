try:
    import socket
except ImportError:
    import usocket as socket

try:
    import struct
except ImportError:
    import ustruct as struct


class MQTTException(Exception):
    pass


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


class MQTTClient:
    def __init__(self, client_id, server, port=1883, keepalive=60):
        self.client_id = _as_bytes(client_id)
        self.server = server
        self.port = int(port)
        self.keepalive = int(keepalive)
        self.sock = None

    def connect(self, clean_session=True):
        self.disconnect()

        sockaddr = socket.getaddrinfo(self.server, self.port)[0][-1]
        sock = socket.socket()
        sock.connect(sockaddr)

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
