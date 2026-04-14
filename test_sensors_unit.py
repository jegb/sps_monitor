#!/usr/bin/env python3
"""
Unit test utility for individual sensor probing and validation.
Tests each sensor independently via direct I2C/GPIO interaction.
Use before full system integration to pre-validate sensor connectivity.

Usage:
    python3 test_sensors_unit.py --scan              # Scan I2C bus
    python3 test_sensors_unit.py --sht3x             # Test SHT3x sensor
    python3 test_sensors_unit.py --sps30             # Test SPS30 sensor
    python3 test_sensors_unit.py --dht11             # Test DHT11 sensor
    python3 test_sensors_unit.py --ppd42             # Test PPD42 dust sensor
    python3 test_sensors_unit.py --all               # Test all sensors
"""

import argparse
import sys
import time


def scan_i2c_bus():
    """Scan I2C bus for connected devices."""
    print("\n" + "="*60)
    print("I2C BUS SCAN")
    print("="*60)
    try:
        # Import board FIRST to ensure busio gets the right one
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        sys.modules['board'] = raspi_40pin

        import busio
        from adafruit_blinka.board.raspberrypi.raspi_40pin import SCL, SDA

        print("Initializing I2C bus (GPIO2/SDA, GPIO3/SCL)...")
        i2c = busio.I2C(SCL, SDA)

        print(f"{'Address':<12} {'Hex':<8} {'Device':<30}")
        print("-" * 50)

        found_devices = []
        for addr in range(0x08, 0x78):
            try:
                if i2c.try_lock():
                    try:
                        i2c.writeto(addr, b'')
                    except OSError:
                        pass
                    finally:
                        i2c.unlock()

                    # Check if device responded
                    if i2c.try_lock():
                        try:
                            result = i2c.readfrom(addr, 1)
                            device_name = _identify_device(addr)
                            found_devices.append((addr, device_name))
                            print(f"0x{addr:02X}       0x{addr:02X}     {device_name}")
                        except (OSError, RuntimeError):
                            pass
                        finally:
                            i2c.unlock()
            except Exception as e:
                pass

        i2c.deinit()

        if not found_devices:
            print("No I2C devices found on bus.")
        else:
            print(f"\nFound {len(found_devices)} device(s).")

    except ImportError:
        print("ERROR: Adafruit CircuitPython library not installed.")
        print("Install with: pip3 install adafruit-circuitpython-busio")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: I2C scan failed: {e}")
        sys.exit(1)


def _identify_device(addr):
    """Identify I2C device by address."""
    known_devices = {
        0x44: "SHT3X (default addr, ADDR→GND)",
        0x45: "SHT3X (alt addr, ADDR→VDD)",
        0x68: "SPS30",
        0x77: "BME280/BMP280 (alt addr)",
        0x76: "BME280/BMP280 (default addr)",
    }
    return known_devices.get(addr, "Unknown device")


def test_sht3x(address=0x44, iterations=3):
    """Test SHT3x sensor (SHT30, SHT31, SHT35)."""
    print("\n" + "="*60)
    print(f"SHT3X SENSOR TEST (I2C Address: 0x{address:02X})")
    print("="*60)

    try:
        # Import board FIRST to ensure busio gets the right one
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        sys.modules['board'] = raspi_40pin

        import busio
        import adafruit_sht31d
        from adafruit_blinka.board.raspberrypi.raspi_40pin import SCL, SDA

        print(f"Connecting to SHT3x at 0x{address:02X}...")
        i2c = busio.I2C(SCL, SDA)
        sensor = adafruit_sht31d.SHT31D(i2c, address=address)

        print(f"{'Attempt':<10} {'Temp (°C)':<15} {'Humidity (%RH)':<20} {'Status'}")
        print("-" * 70)

        for i in range(1, iterations + 1):
            try:
                temp = sensor.temperature
                humidity = sensor.relative_humidity

                if temp is None or humidity is None:
                    print(f"{i:<10} {'N/A':<15} {'N/A':<20} FAILED - None returned")
                else:
                    status = "✓ OK"
                    print(f"{i:<10} {temp:<15.2f} {humidity:<20.2f} {status}")

            except Exception as e:
                print(f"{i:<10} {'ERROR':<15} {'ERROR':<20} {str(e)}")
                sys.exit(1)

            if i < iterations:
                time.sleep(1)

        i2c.deinit()
        print("\n✓ SHT3x test PASSED")

    except ImportError as e:
        print(f"ERROR: Required library not installed: {e}")
        print("Install with: pip3 install adafruit-circuitpython-sht31d")
        sys.exit(1)
    except Exception as e:
        print(f"✗ SHT3x test FAILED: {e}")
        sys.exit(1)


def test_sps30(iterations=3):
    """Test SPS30 sensor."""
    print("\n" + "="*60)
    print("SPS30 SENSOR TEST (I2C Address: 0x68)")
    print("="*60)

    try:
        from c_sps30_i2c.sps30_ctypes_wrapper import read_sps30

        print("Starting SPS30 measurement sequence...")
        print("(SPS30 requires 8+ seconds for data to stabilize)\n")

        print(f"{'Attempt':<10} {'PM1.0':<12} {'PM2.5':<12} {'PM4.0':<12} {'PM10.0':<12} {'Status'}")
        print("-" * 80)

        for i in range(1, iterations + 1):
            try:
                data = read_sps30()

                if data is None:
                    print(f"{i:<10} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12} FAILED")
                else:
                    status = "✓ OK"
                    print(f"{i:<10} {data.mc_1p0:<12.2f} {data.mc_2p5:<12.2f} "
                          f"{data.mc_4p0:<12.2f} {data.mc_10p0:<12.2f} {status}")

            except Exception as e:
                print(f"{i:<10} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {'ERROR':<12} {str(e)[:20]}")
                sys.exit(1)

            if i < iterations:
                time.sleep(10)  # SPS30 needs time between reads

        print("\n✓ SPS30 test PASSED")

    except ImportError:
        print("ERROR: SPS30 driver not found at c_sps30_i2c/sps30_ctypes_wrapper.py")
        sys.exit(1)
    except Exception as e:
        print(f"✗ SPS30 test FAILED: {e}")
        sys.exit(1)


def test_dht11(pin=4, iterations=3):
    """Test DHT11 sensor (GPIO-based)."""
    print("\n" + "="*60)
    print(f"DHT11 SENSOR TEST (GPIO Pin: {pin})")
    print("="*60)

    try:
        # Import board FIRST to ensure adafruit_dht gets the right one
        from adafruit_blinka.board.raspberrypi import raspi_40pin
        sys.modules['board'] = raspi_40pin

        import adafruit_dht
        from adafruit_blinka.board.raspberrypi.raspi_40pin import D4, D17, D22, D27

        print(f"Connecting to DHT11 on GPIO{pin}...")

        # Map pin number to board pin
        pin_map = {
            4: D4,
            17: D17,
            27: D27,
            22: D22,
        }

        if pin not in pin_map:
            print(f"ERROR: GPIO pin {pin} not in supported map. Supported: {list(pin_map.keys())}")
            sys.exit(1)

        sensor = adafruit_dht.DHT11(pin_map[pin])

        print(f"{'Attempt':<10} {'Temp (°C)':<15} {'Humidity (%RH)':<20} {'Status'}")
        print("-" * 70)

        for i in range(1, iterations + 1):
            try:
                temp = sensor.temperature
                humidity = sensor.humidity

                if temp is None or humidity is None:
                    print(f"{i:<10} {'N/A':<15} {'N/A':<20} FAILED - None returned")
                else:
                    status = "✓ OK"
                    print(f"{i:<10} {temp:<15.1f} {humidity:<20.1f} {status}")

            except RuntimeError as e:
                print(f"{i:<10} {'ERROR':<15} {'ERROR':<20} {str(e)[:30]}")
                # DHT11 can fail intermittently, retry
                time.sleep(2)
                continue
            except Exception as e:
                print(f"{i:<10} {'ERROR':<15} {'ERROR':<20} {str(e)[:30]}")
                sys.exit(1)

            if i < iterations:
                time.sleep(2)  # DHT11 needs 2 seconds between reads

        sensor.deinit()
        print("\n✓ DHT11 test PASSED")

    except ImportError as e:
        print(f"ERROR: Required library not installed: {e}")
        print("Install with: pip3 install adafruit-circuitpython-dht")
        sys.exit(1)
    except Exception as e:
        print(f"✗ DHT11 test FAILED: {e}")
        sys.exit(1)


def test_ppd42(pin=23, particle_size=2.5, sample_duration=5, iterations=3):
    """Test PPD42 dust sensor (GPIO-based)."""
    print("\n" + "="*60)
    print(f"PPD42 DUST SENSOR TEST (GPIO Pin: {pin}, PM{particle_size})")
    print("="*60)

    try:
        from sensors.ppd42 import PPD42Sensor

        print(f"Connecting to PPD42 on GPIO{pin}...")
        sensor = PPD42Sensor(pin=pin, particle_size=particle_size)

        print(f"{'Attempt':<10} {'Particle Count':<20} {'Unit':<20} {'Status'}")
        print("-" * 70)

        for i in range(1, iterations + 1):
            try:
                reading = sensor.get_reading(sample_duration=sample_duration)

                if reading is None:
                    print(f"{i:<10} {'N/A':<20} {'N/A':<20} FAILED - None returned")
                else:
                    status = "✓ OK"
                    particle_count = reading.get("particle_count", 0)
                    unit = reading.get("unit", "unknown")
                    print(f"{i:<10} {particle_count:<20.2f} {unit:<20} {status}")

            except Exception as e:
                print(f"{i:<10} {'ERROR':<20} {'ERROR':<20} {str(e)[:30]}")
                sys.exit(1)

            if i < iterations:
                time.sleep(2)  # PPD42 needs time between reads

        sensor.cleanup()
        print("\n✓ PPD42 test PASSED")

    except ImportError as e:
        print(f"ERROR: Required library not installed or sensor module not found: {e}")
        print("Ensure sensors/ppd42.py exists and RPi.GPIO is installed")
        sys.exit(1)
    except Exception as e:
        print(f"✗ PPD42 test FAILED: {e}")
        sys.exit(1)


def test_all_sensors():
    """Test all available sensors."""
    print("\n" + "="*60)
    print("COMPREHENSIVE SENSOR TEST SUITE")
    print("="*60)

    results = []

    # Test I2C bus
    try:
        scan_i2c_bus()
        results.append(("I2C Bus Scan", "PASSED"))
    except SystemExit:
        results.append(("I2C Bus Scan", "FAILED"))

    # Test SHT3x
    try:
        test_sht3x(iterations=1)
        results.append(("SHT3x Sensor", "PASSED"))
    except SystemExit:
        results.append(("SHT3x Sensor", "FAILED"))
    except Exception:
        results.append(("SHT3x Sensor", "SKIPPED"))

    # Test SPS30
    try:
        test_sps30(iterations=1)
        results.append(("SPS30 Sensor", "PASSED"))
    except SystemExit:
        results.append(("SPS30 Sensor", "FAILED"))
    except Exception:
        results.append(("SPS30 Sensor", "SKIPPED"))

    # Test DHT11
    try:
        from config import DHT11_PIN
        test_dht11(pin=DHT11_PIN, iterations=1)
        results.append(("DHT11 Sensor", "PASSED"))
    except SystemExit:
        results.append(("DHT11 Sensor", "FAILED"))
    except Exception:
        results.append(("DHT11 Sensor", "SKIPPED"))

    # Test PPD42
    try:
        from config import PPD42_ENABLED, PPD42_PIN, PPD42_PARTICLE_SIZE
        if PPD42_ENABLED:
            test_ppd42(pin=PPD42_PIN, particle_size=PPD42_PARTICLE_SIZE, sample_duration=5, iterations=1)
            results.append(("PPD42 Sensor", "PASSED"))
        else:
            results.append(("PPD42 Sensor", "DISABLED"))
    except SystemExit:
        results.append(("PPD42 Sensor", "FAILED"))
    except Exception:
        results.append(("PPD42 Sensor", "SKIPPED"))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"{'Test':<25} {'Result':<15}")
    print("-" * 40)
    for test_name, result in results:
        print(f"{test_name:<25} {result:<15}")


def main():
    parser = argparse.ArgumentParser(
        description="Unit test utility for individual sensor probing and validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_sensors_unit.py --scan          # Scan I2C bus
  python3 test_sensors_unit.py --sht3x         # Test SHT3x sensor
  python3 test_sensors_unit.py --sps30         # Test SPS30 sensor
  python3 test_sensors_unit.py --dht11         # Test DHT11 sensor
  python3 test_sensors_unit.py --ppd42         # Test PPD42 dust sensor
  python3 test_sensors_unit.py --all           # Test all sensors
  python3 test_sensors_unit.py --sht3x --addr 0x45  # Test SHT3x at alt address
  python3 test_sensors_unit.py --ppd42 --ppd42-size 10  # Test PPD42 as PM10
        """
    )

    parser.add_argument("--scan", action="store_true", help="Scan I2C bus for devices")
    parser.add_argument("--sht3x", action="store_true", help="Test SHT3x sensor")
    parser.add_argument("--sps30", action="store_true", help="Test SPS30 sensor")
    parser.add_argument("--dht11", action="store_true", help="Test DHT11 sensor")
    parser.add_argument("--ppd42", action="store_true", help="Test PPD42 dust sensor")
    parser.add_argument("--all", action="store_true", help="Test all sensors")
    parser.add_argument("--addr", type=str, default="0x44",
                       help="I2C address for SHT3x (default: 0x44)")
    parser.add_argument("--pin", type=int, default=4,
                       help="GPIO pin for DHT11 (default: 4)")
    parser.add_argument("--ppd42-pin", type=int, default=23,
                       help="GPIO pin for PPD42 (default: 23)")
    parser.add_argument("--ppd42-size", type=float, default=2.5,
                       help="Particle size for PPD42 in µm (default: 2.5 for PM2.5)")
    parser.add_argument("--iterations", "-n", type=int, default=3,
                       help="Number of read iterations per sensor (default: 3)")

    args = parser.parse_args()

    # Parse address if provided
    try:
        address = int(args.addr, 16) if args.addr.startswith("0x") else int(args.addr)
    except ValueError:
        print(f"ERROR: Invalid address format: {args.addr}")
        sys.exit(1)

    # Run tests
    if args.scan:
        scan_i2c_bus()
    elif args.sht3x:
        test_sht3x(address=address, iterations=args.iterations)
    elif args.sps30:
        test_sps30(iterations=args.iterations)
    elif args.dht11:
        test_dht11(pin=args.pin, iterations=args.iterations)
    elif args.ppd42:
        test_ppd42(pin=args.ppd42_pin, particle_size=args.ppd42_size, sample_duration=5, iterations=args.iterations)
    elif args.all:
        test_all_sensors()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
