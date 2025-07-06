import time
import argparse
from c_sps30_i2c.sps30_ctypes_wrapper import read_sps30
from config import SENSOR_TYPE

if SENSOR_TYPE == "SHT31":
    from sensors import sht31 as temp_sensor
elif SENSOR_TYPE == "DHT11":
    from sensors import dht11 as temp_sensor
else:
    raise ValueError("Unsupported sensor")

def test_read():
    print("[INFO] Reading SPS30 sensor...")
    data = read_sps30()
    print(f"PM1.0:  {data.mc_1p0:.1f} µg/m³")
    print(f"PM2.5:  {data.mc_2p5:.1f} µg/m³")
    print(f"PM4.0:  {data.mc_4p0:.1f} µg/m³")
    print(f"PM10.0: {data.mc_10p0:.1f} µg/m³")
    print(f"Size:   {data.typical_particle_size:.2f} µm")

    print("[INFO] Reading temperature and humidity sensor...")
    temp, humidity = temp_sensor.get_readings()
    print(f"Temp:   {temp:.1f} °C")
    print(f"Hum:    {humidity:.1f} %")

def main():
    parser = argparse.ArgumentParser(description="CLI tester for SPS30 and temp/humidity sensors")
    parser.add_argument("--read", action="store_true", help="Perform one-time sensor readout")
    args = parser.parse_args()

    if args.read:
        test_read()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
