import os
import ctypes
import time

lib_path = os.path.join(os.path.dirname(__file__), 'libsps30.so')
sps30 = ctypes.CDLL(lib_path)

class SPS30Measurement(ctypes.Structure):
    _fields_ = [
        ("mc_1p0", ctypes.c_float),
        ("mc_2p5", ctypes.c_float),
        ("mc_4p0", ctypes.c_float),
        ("mc_10p0", ctypes.c_float),
        ("nc_0p5", ctypes.c_float),
        ("nc_1p0", ctypes.c_float),
        ("nc_2p5", ctypes.c_float),
        ("nc_4p0", ctypes.c_float),
        ("nc_10p0", ctypes.c_float),
        ("typical_particle_size", ctypes.c_float),
    ]

def read_sps30(timeout=30):
    """
    Read measurement from SPS30 sensor.

    Args:
        timeout: Maximum seconds to wait for data ready (default: 30)

    Returns:
        SPS30Measurement object

    Raises:
        TimeoutError: If sensor doesn't respond within timeout
    """
    sps30.sps30_start_measurement()
    time.sleep(8)

    data_ready = ctypes.c_uint16()
    elapsed = 0
    while elapsed < timeout:
        sps30.sps30_read_data_ready(ctypes.byref(data_ready))
        if data_ready.value:
            break
        time.sleep(1)
        elapsed += 1

    if elapsed >= timeout:
        sps30.sps30_stop_measurement()
        raise TimeoutError(f"SPS30 sensor did not respond within {timeout} seconds")

    measurement = SPS30Measurement()
    sps30.sps30_read_measurement(ctypes.byref(measurement))
    sps30.sps30_stop_measurement()
    return measurement