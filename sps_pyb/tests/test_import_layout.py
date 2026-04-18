import importlib
import sys
import unittest
from pathlib import Path


class ImportLayoutTests(unittest.TestCase):
    def test_board_style_app_imports_work(self):
        flash_lib = Path(__file__).resolve().parents[1] / "flash" / "lib"
        flash_lib_str = str(flash_lib)
        added = False

        if flash_lib_str not in sys.path:
            sys.path.insert(0, flash_lib_str)
            added = True

        try:
            mqtt_client = importlib.import_module("app.mqtt_client")
            runtime = importlib.import_module("app.runtime")

            self.assertTrue(hasattr(mqtt_client, "MQTTPublisher"))
            self.assertTrue(hasattr(runtime, "StationRuntime"))
        finally:
            for name in (
                "app.mqtt_client",
                "app.runtime",
                "app.payload",
                "app.storage",
                "app.time_sync",
                "app.wifi",
                "sensors.aht10",
                "sensors.sht3x",
                "sensors.sps30",
                "umqtt.simple",
            ):
                sys.modules.pop(name, None)

            if added:
                sys.path.remove(flash_lib_str)


if __name__ == "__main__":
    unittest.main()
