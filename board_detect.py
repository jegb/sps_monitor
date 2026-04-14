"""
Auto-detect Raspberry Pi model and load appropriate board module.
Supports RPi 2, 3, 4, 5, Zero, Zero W, and variants.
"""

import sys
from pathlib import Path


def get_rpi_model():
    """Detect Raspberry Pi model from device tree."""
    try:
        model_file = Path("/proc/device-tree/model")
        if model_file.exists():
            model = model_file.read_text().strip().rstrip('\x00')
            return model
    except:
        pass
    return "Unknown"


def get_board_module():
    """
    Auto-detect RPi model and return appropriate adafruit_blinka board module.
    """
    model = get_rpi_model()
    print(f"Detected: {model}")

    # Map models to board modules
    if "Raspberry Pi 5" in model:
        from adafruit_blinka.board.raspberrypi import raspi_5
        return raspi_5, "raspi_5"
    elif "Raspberry Pi 4" in model:
        from adafruit_blinka.board.raspberrypi import raspi_4b
        return raspi_4b, "raspi_4b"
    elif "Raspberry Pi 3" in model or "Raspberry Pi 2" in model:
        # Both Pi 2 and Pi 3 use 40-pin header
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        return raspi_40pin, "raspi_40pin"
    elif "Raspberry Pi Zero" in model:
        # Pi Zero variants - use generic 40pin mapping (works for GPIO layout)
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        return raspi_40pin, "raspi_40pin"
    elif "Raspberry Pi" in model:
        # Fallback for any other RPi - assume 40-pin header
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        return raspi_40pin, "raspi_40pin"
    else:
        # Fallback if device tree read fails
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        return raspi_40pin, "raspi_40pin"


def init_board():
    """
    Initialize board module in sys.modules.
    Call this BEFORE importing busio, adafruit_dht, etc.
    """
    board_module, board_name = get_board_module()
    sys.modules['board'] = board_module
    return board_module, board_name
