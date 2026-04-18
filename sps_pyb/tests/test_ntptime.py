import unittest
from unittest import mock

from sps_pyb.flash import ntptime


class NTPTimeTests(unittest.TestCase):
    def test_ntp_delta_matches_runtime_epoch(self):
        epoch_year = ntptime._time.gmtime(0)[0]
        expected = (
            ntptime.NTP_DELTA_2000
            if epoch_year == 2000
            else ntptime.NTP_DELTA_1970
        )
        self.assertEqual(ntptime._ntp_delta(), expected)

    def test_rtc_datetime_tuple_matches_gmtime_layout(self):
        rtc_tuple = ntptime._rtc_datetime_tuple(0)
        gmt = ntptime._time.gmtime(0)

        self.assertEqual(rtc_tuple[0], gmt[0])
        self.assertEqual(rtc_tuple[1], gmt[1])
        self.assertEqual(rtc_tuple[2], gmt[2])
        self.assertEqual(rtc_tuple[3], gmt[6] + 1)
        self.assertEqual(rtc_tuple[4], gmt[3])
        self.assertEqual(rtc_tuple[5], gmt[4])
        self.assertEqual(rtc_tuple[6], gmt[5])
        self.assertEqual(rtc_tuple[7], 0)

    def test_host_candidates_accepts_comma_separated_list(self):
        self.assertEqual(
            ntptime._host_candidates("pool.ntp.org, time.cloudflare.com , time.google.com"),
            ["pool.ntp.org", "time.cloudflare.com", "time.google.com"],
        )

    def test_time_retries_multiple_hosts(self):
        reply = bytearray(48)
        transmit_seconds = ntptime._ntp_delta() + 123
        reply[40:44] = ntptime.struct.pack("!I", transmit_seconds)

        class FakeSocket:
            def __init__(self):
                self.closed = False

            def settimeout(self, timeout):
                self.timeout = timeout

            def sendto(self, _query, _address):
                pass

            def recv(self, _size):
                return bytes(reply)

            def close(self):
                self.closed = True

        calls = []

        def fake_getaddrinfo(name, port):
            calls.append((name, port))
            if name == "bad.example":
                raise OSError("dns failed")
            return [(ntptime.socket.AF_INET, ntptime.socket.SOCK_DGRAM, 0, "", ("1.2.3.4", port))]

        with (
            mock.patch.object(ntptime.socket, "getaddrinfo", side_effect=fake_getaddrinfo),
            mock.patch.object(ntptime.socket, "socket", return_value=FakeSocket()),
        ):
            self.assertEqual(
                ntptime.time(host_override="bad.example,good.example", timeout_s=2),
                123,
            )

        self.assertEqual(calls, [("bad.example", 123), ("good.example", 123)])

    def test_recv_message_prefers_recvfrom_when_available(self):
        class FakeSocket:
            def recvfrom(self, _size):
                return (b"abc", ("1.2.3.4", 123))

        self.assertEqual(ntptime._recv_message(FakeSocket(), 3), b"abc")


if __name__ == "__main__":
    unittest.main()
