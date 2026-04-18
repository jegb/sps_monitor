import importlib
import sys
import unittest
from pathlib import Path


class _FakeSocket:
    def __init__(self):
        self.timeout = None
        self.closed = False
        self.sent = []
        self.recv_payloads = [b"\x20\x02\x00\x00"]
        self.connect_attempts = 0

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, sockaddr):
        self.connect_attempts += 1
        if self.connect_attempts == 1:
            raise OSError(115)
        raise OSError(106)

    def send(self, payload):
        self.sent.append(bytes(payload))
        return len(payload)

    def recv(self, size):
        if not self.recv_payloads:
            return b""
        payload = self.recv_payloads.pop(0)
        chunk, remainder = payload[:size], payload[size:]
        if remainder:
            self.recv_payloads.insert(0, remainder)
        return chunk

    def close(self):
        self.closed = True


class _FakeSocketModule:
    SOCK_STREAM = 1

    def __init__(self):
        self.last_socket = None

    def getaddrinfo(self, server, port, family=0, socktype=0):
        return [(2, self.SOCK_STREAM, 6, "", (server, port))]

    def socket(self, family, socktype, proto):
        self.last_socket = _FakeSocket()
        return self.last_socket


class _FakePoller:
    def __init__(self):
        self.timeout = None

    def register(self, sock, eventmask):
        self.sock = sock
        self.eventmask = eventmask

    def poll(self, timeout):
        self.timeout = timeout
        return [(1, _FakeSelectModule.POLLOUT)]


class _FakeSelectModule:
    POLLOUT = 0x04
    POLLERR = 0x08
    POLLHUP = 0x10

    def __init__(self):
        self.last_poller = None

    def poll(self):
        self.last_poller = _FakePoller()
        return self.last_poller


class UmqttSimpleTests(unittest.TestCase):
    def test_connect_accepts_einprogress_and_completes_handshake(self):
        flash_lib = Path(__file__).resolve().parents[1] / "flash" / "lib"
        flash_lib_str = str(flash_lib)
        added = False

        if flash_lib_str not in sys.path:
            sys.path.insert(0, flash_lib_str)
            added = True

        try:
            simple = importlib.import_module("umqtt.simple")
            original_socket = simple.socket
            original_select = simple.select

            fake_socket_module = _FakeSocketModule()
            fake_select_module = _FakeSelectModule()
            simple.socket = fake_socket_module
            simple.select = fake_select_module

            try:
                client = simple.MQTTClient("client-1", "broker.local", port=1883)
                session_present = client.connect()
            finally:
                simple.socket = original_socket
                simple.select = original_select

            self.assertFalse(session_present)
            self.assertIsNotNone(fake_socket_module.last_socket)
            self.assertEqual(fake_socket_module.last_socket.timeout, 5)
            self.assertEqual(fake_socket_module.last_socket.connect_attempts, 2)
            self.assertTrue(fake_socket_module.last_socket.sent)
            self.assertEqual(fake_socket_module.last_socket.sent[0][0], 0x10)
            self.assertIsNotNone(fake_select_module.last_poller)
            self.assertEqual(fake_select_module.last_poller.timeout, 100)
        finally:
            sys.modules.pop("umqtt.simple", None)
            if added:
                sys.path.remove(flash_lib_str)


if __name__ == "__main__":
    unittest.main()
