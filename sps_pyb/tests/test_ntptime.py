import unittest

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


if __name__ == "__main__":
    unittest.main()
