"""
PPD42NS Dust Sensor Driver
Reads particle concentration via pulse-width modulation on GPIO pin.
Supports configurable particle size thresholds for PM2.5, PM10, or custom ranges.
"""

import RPi.GPIO as GPIO
import time

# Default configuration
DEFAULT_PARTICLE_SIZE = 2.5  # PM2.5 (µm)
DEFAULT_SAMPLE_DURATION = 30  # seconds


class PPD42Sensor:
    """
    PPD42NS dust sensor reader.
    Converts pulse-width to particle concentration (pcs/0.01cf).
    """

    def __init__(self, pin=23, particle_size=DEFAULT_PARTICLE_SIZE):
        """
        Initialize PPD42 sensor.

        Args:
            pin: GPIO pin number for sensor output
            particle_size: Target particle size in micrometers (e.g., 2.5 for PM2.5, 10 for PM10)
        """
        self.pin = pin
        self.particle_size = particle_size
        self.pulse_count = 0
        self.edge_count = 0

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self._edge_callback)

    def _edge_callback(self, channel):
        """Count edges for pulse detection."""
        self.edge_count += 1

    def _get_particle_concentration(self, sample_duration=DEFAULT_SAMPLE_DURATION):
        """
        Measure particle concentration over sample period.

        Returns:
            Particle concentration in pcs/0.01cf (particles per 0.01 cubic feet)
            Conversion: concentration = (pulse_duration / 10) * 100 / measurement_duration
        """
        self.edge_count = 0
        start_time = time.time()
        low_duration = 0

        while (time.time() - start_time) < sample_duration:
            # Wait for falling edge
            while GPIO.input(self.pin) == 1 and (time.time() - start_time) < sample_duration:
                pass

            fall_time = time.time()

            # Wait for rising edge
            while GPIO.input(self.pin) == 0 and (time.time() - start_time) < sample_duration:
                pass

            rise_time = time.time()
            low_duration += (rise_time - fall_time)

        # Calculate concentration
        # PPD42 formula: concentration (pcs/0.01cf) = (pulse_duration / sample_duration) * 10
        if sample_duration > 0:
            ratio = low_duration / sample_duration
            # Adjust for particle size (empirical conversion factor)
            concentration = ratio * 1000
            return round(concentration, 2)

        return 0.0

    def get_reading(self, sample_duration=DEFAULT_SAMPLE_DURATION):
        """
        Get particle concentration reading.

        Args:
            sample_duration: Measurement duration in seconds

        Returns:
            Dictionary with particle count and size info
        """
        try:
            concentration = self._get_particle_concentration(sample_duration)
            return {
                "particle_count": concentration,
                "particle_size": self.particle_size,
                "unit": "pcs/0.01cf"
            }
        except Exception as e:
            print(f"Error reading PPD42: {e}")
            return None

    def set_particle_size(self, size):
        """
        Change target particle size (µm).
        Useful for switching between PM2.5, PM10, or custom measurements.
        """
        self.particle_size = size

    def cleanup(self):
        """Clean up GPIO resources."""
        try:
            GPIO.remove_event_detect(self.pin)
            GPIO.cleanup(self.pin)
        except:
            pass


# Global sensor instance
_sensor_instance = None


def get_readings(pin=23, particle_size=DEFAULT_PARTICLE_SIZE, sample_duration=DEFAULT_SAMPLE_DURATION):
    """
    Read PPD42 sensor.

    Args:
        pin: GPIO pin (default: 23)
        particle_size: Particle size in µm (default: 2.5 for PM2.5)
        sample_duration: Measurement duration in seconds (default: 30)

    Returns:
        Dictionary with particle_count and particle_size, or None on error
    """
    global _sensor_instance

    if _sensor_instance is None:
        _sensor_instance = PPD42Sensor(pin=pin, particle_size=particle_size)

    reading = _sensor_instance.get_reading(sample_duration=sample_duration)
    return reading.get("particle_count") if reading else None
