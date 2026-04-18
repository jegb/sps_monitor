# `sps_pyb`

MicroPython port of the sensor node for the `pybd-sf6w`.

This target intentionally keeps only the device-side responsibilities:

- read `SPS30`
- optionally read `PPD42`
- read one environmental sensor (`SHT3x`, `SHT20`, `AHT10`, or `DHT11`)
- connect to Wi-Fi
- publish raw MQTT payloads to `airquality/sensor`
- store SD-backed CSV history
- store SD-backed offline replay data

It does not include Flask, SQLite, `db_metrics`, Raspberry Pi GPIO helpers, Adafruit IO, or the Pi dashboard.

## Status

The current pyboard work proves out:

- Wi-Fi + MQTT on `PYBD-SF6W`
- environmental sensors such as `AHT10`
- `PPD42` experimentation and host-side calibration tooling

The `PPD42` path is experimental and did not prove strong enough for production PM estimation in this project.

## TODO

- port and validate the `SPS30` path on the pyboard later if the board is revisited as a real particulate node

## Layout

```text
sps_pyb/
  README.md
  flash/
    boot.py
    main.py
    config.py.example
    lib/
      app/
      sensors/
      umqtt/
  tests/
```

## MQTT Contract

The board publishes raw sensor values only:

```json
{
  "pm_1_0": 1.2,
  "pm_2_5": 2.3,
  "pm_4_0": 3.4,
  "pm_10_0": 4.5,
  "temp": 25.1,
  "humidity": 59.6
}
```

The topic remains `airquality/sensor`.

If `PPD42` is enabled, the payload also includes:

```json
{
  "ppd42_particle_count": 12.3456,
  "ppd42_particle_size": 2.5
}
```

For `rpi_watch` compatibility, `PPD42` can also synthesize `pm_1_0`, `pm_2_5`, `pm_4_0`, and `pm_10_0` using a sample-and-hold ring. In that mode, each new `PPD42` sample updates one PM field and the other three keep their previous values until their turn.

If you need a stricter `rpi_watch`-compatible MQTT contract, `PPD42` can also estimate a single `pm_2_5` value from `particle_count` and omit non-contract fields from the live MQTT payload.

## Environmental Sensor Options

`sps_pyb` now supports four temperature/humidity sensor choices:

- `sht3x` on I2C
- `sht20` on I2C
- `aht10` on I2C
- `dht11` on a single GPIO pin

Set `ENV_SENSOR` in `sps_pyb/flash/config.py` to choose which one to use.

### Pyboard Wiring

For the existing hardware I2C bus, MicroPython maps `I2C('X')` to `X9` = `SCL` and `X10` = `SDA`. 

Recommended wiring:

- `SHT20`
  - `VCC` -> pyboard `3V3`
  - `GND` -> pyboard `GND`
  - `SCL` -> pyboard `X9`
  - `SDA` -> pyboard `X10`
- `AHT10`
  - `VCC` -> pyboard `3V3`
  - `GND` -> pyboard `GND`
  - `SCL` -> pyboard `X9`
  - `SDA` -> pyboard `X10`
- `DHT11`
  - `VCC` -> pyboard `3V3`
  - `GND` -> pyboard `GND`
  - `DATA` -> pyboard `X1`
  - add a `4.7k` to `10k` pull-up from `DATA` to `3V3` if your module does not already include one

If you keep the SPS30 on the same I2C bus, it can share `X9`/`X10`; the SPS30 is on address `0x69`, the SHT20/SHT2x family uses `0x40`, and the AHT10 uses `0x38`.

### Config Examples

Current default `SHT3x`:

```python
ENV_SENSOR = "sht3x"
SHT3X_ADDR = 0x44
```

Switch to `SHT20`:

```python
ENV_SENSOR = "sht20"
SHT20_ADDR = 0x40
```

Switch to `AHT10`:

```python
ENV_SENSOR = "aht10"
AHT10_ADDR = 0x38
```

Switch to `DHT11`:

```python
ENV_SENSOR = "dht11"
DHT11_PIN = "X1"
```

Run with only `AHT10` connected:

```python
SPS30_ENABLED = False
ENV_SENSOR = "aht10"
AHT10_ADDR = 0x38
```

In that mode, `main.py` still runs and publishes/stores `temp` and `humidity`; the `pm_*` fields are left empty.

## PPD42

`PPD42` is supported as an optional digital pulse-output sensor.

Suggested pyboard wiring:

- `PPD42 OUT` -> pyboard `X2`
- `PPD42 GND` -> pyboard `GND`
- `PPD42 VCC` -> your sensor supply

Configure it in `sps_pyb/flash/config.py`:

```python
PPD42_ENABLED = True
PPD42_PIN = "X2"
PPD42_PARTICLE_SIZE = 2.5
PPD42_SAMPLE_DURATION = 30
PPD42_COMPAT_MODE = "none"
PPD42_PARTICLE_DENSITY_KG_M3 = 1650.0
PPD42_MASS_CALIBRATION_FACTOR = 1.0
```

When enabled, the runtime spends `PPD42_SAMPLE_DURATION` seconds accumulating low-pulse occupancy during each loop.

### `rpi_watch` Compatibility Mode

If you want a `PPD42`-only node to feed the existing `rpi_watch` PM payload shape, enable:

```python
PPD42_ENABLED = True
PPD42_SAMPLE_DURATION = 30
PUBLISH_INTERVAL_S = 30
PPD42_COMPAT_MODE = "hold4_pm_fields"
```

That mode updates the synthetic PM fields in this sequence:

1. `pm_1_0`
2. `pm_2_5`
3. `pm_4_0`
4. `pm_10_0`

Each field holds its most recent assigned `PPD42` sample until the next four-step cycle reaches it again.

This is a compatibility shim only. It does not turn the `PPD42` into a true simultaneous PM1.0/PM2.5/PM4.0/PM10 sensor.

### Strict `pm_2_5` Contract Mode

If you want MQTT output that stays within the original `rpi_watch` contract, map `PPD42` to an estimated `pm_2_5` value and strip non-contract fields from the live payload:

```python
PPD42_ENABLED = True
PPD42_SAMPLE_DURATION = 30
PUBLISH_INTERVAL_S = 30
PPD42_COMPAT_MODE = "pm25_mass_estimate"
PPD42_PARTICLE_DENSITY_KG_M3 = 1650.0
PPD42_MASS_CALIBRATION_FACTOR = 1.0
MQTT_STRICT_CONTRACT = True
```

In that mode the MQTT payload contains only contract fields, and `pm_2_5` is estimated from `PPD42` particle count using particle size, density, and a calibration factor. This is still an estimate and should be calibrated against a reference sensor if you need absolute values.

## Direct REPL Reads

Open a REPL on the board:

```sh
mpremote connect auto repl
```

Then add the board library path once:

```python
import sys, config
if "/flash/lib" not in sys.path:
    sys.path.append("/flash/lib")
```

### Read `AHT10` directly

```python
from machine import I2C
from sensors.aht10 import AHT10Sensor

i2c = I2C(config.I2C_BUS, freq=config.I2C_FREQ)
sensor = AHT10Sensor(i2c, address=config.AHT10_ADDR)
print(sensor.read_temperature_humidity())
```

Expected shape:

```python
(25.36, 44.28)
```

### Read `PPD42` directly

```python
from sensors.ppd42 import PPD42Sensor

sensor = PPD42Sensor(
    pin=config.PPD42_PIN,
    particle_size=config.PPD42_PARTICLE_SIZE,
)
print(sensor.get_reading(sample_duration=config.PPD42_SAMPLE_DURATION))
```

Expected shape:

```python
{
    "particle_count": 97.2072,
    "particle_size": 2.5,
    "low_occupancy_us": 486036,
    "unit": "pcs/0.01cf",
}
```

### Build the exact payload that would go to MQTT

This inspects the runtime output without actually publishing:

```python
from app.runtime import StationRuntime
from app.payload import dumps_json

runtime = StationRuntime(config)
record = runtime._capture_record()
payload = runtime._build_publish_payload(record)

print(record)
print(payload)
print(dumps_json(payload))
```

For an `AHT10`-only node, the payload looks like:

```python
{
    "pm_1_0": None,
    "pm_2_5": None,
    "pm_4_0": None,
    "pm_10_0": None,
    "temp": 25.5754,
    "humidity": 45.621,
    "ppd42_particle_count": 97.2072,
    "ppd42_particle_size": 2.5,
}
```

If `MQTT_STRICT_CONTRACT = True` and `PPD42_COMPAT_MODE = "pm25_mass_estimate"`, the MQTT payload instead looks like:

```python
{
    "pm_2_5": 0.6867,
    "temp": 27.4881,
    "humidity": 44.1042,
}
```

If `PPD42_COMPAT_MODE = "hold4_pm_fields"`, repeat the capture a few times to see the sample-and-hold PM fields fill in:

```python
from app.runtime import StationRuntime
from app.payload import build_live_payload

runtime = StationRuntime(config)
for _ in range(4):
    record = runtime._capture_record()
    print(build_live_payload(record))
```

## Calibration Ingest

If you want to calibrate `PPD42` against an `SPS30` reference later, keep the main topic strict and publish the raw `PPD42` record on a second topic:

```python
MQTT_TOPIC = "airquality/sensor"
MQTT_STRICT_CONTRACT = True
MQTT_CALIBRATION_TOPIC = "airquality/sensor_ppd42_raw"

PPD42_COMPAT_MODE = "pm25_mass_estimate"
PPD42_SAMPLE_DURATION = 30
PUBLISH_INTERVAL_S = 30
```

In that setup:

- `MQTT_TOPIC` keeps the `rpi_watch` contract
- `MQTT_CALIBRATION_TOPIC` carries the internal record, including `ppd42_particle_count`

Then capture paired rows from MQTT on one host:

```sh
./.venv-tools/bin/python -m sps_pyb.tools.ppd42_calibration capture \
  --broker-host 192.168.0.67 \
  --sample-topic airquality/sensor_ppd42_raw \
  --reference-topic airquality/sensor \
  --output sps_pyb/calibration_ppd42.csv \
  --max-skew-s 45 \
  --max-pairs 200
```

That CSV can then be fit to linear models:

```sh
./.venv-tools/bin/python -m sps_pyb.tools.ppd42_calibration fit \
  --input sps_pyb/calibration_ppd42.csv
```

The fit command prints:

- JSON summary with `a`, `b`, `r2`, and sample count for each PM field
- a `PPD42_LINEAR_PM_CALIBRATION` config snippet you can reuse later

### Offline Split-Capture Workflow

If you don't want the watch to subscribe to the raw `PPD42` topic permanently, keep:

- `rpi_watch` logging `airquality/sensor` into `data/mqtt_records.jsonl`
- the Mac logging `airquality/sensor_ppd42_raw` into a separate JSONL file

Capture the raw `PPD42` stream on the Mac:

```sh
./.venv-tools/bin/python -m sps_pyb.tools.mqtt_trace \
  --broker-host 192.168.0.67 \
  --topic airquality/sensor_ppd42_raw \
  --output sps_pyb/ppd42_raw.jsonl
```

Copy the watch receive log to the Mac:

```sh
scp pi@192.168.0.67:/home/pi/rpi_watch/data/mqtt_records.jsonl sps_pyb/watch_mqtt_records.jsonl
```

Then join the Mac trace with the copied watch JSONL archive into the training CSV:

```sh
./.venv-tools/bin/python -m sps_pyb.tools.join_traces \
  --sample-input sps_pyb/ppd42_raw.jsonl \
  --reference-input sps_pyb/watch_mqtt_records.jsonl \
  --sample-topic airquality/sensor_ppd42_raw \
  --reference-topic airquality/sensor \
  --output sps_pyb/calibration_ppd42.csv \
  --max-skew-s 45
```

That `calibration_ppd42.csv` can then be fit with the same `ppd42_calibration fit` command above.

### Temp-Only Bench Test

If you want to test just the environmental sensor before wiring `SPS30`, deploy the board files and run:

```sh
mpremote connect auto exec "import temp_read; temp_read.run_once()"
```

That reads the sensor selected by `ENV_SENSOR` and prints:

```python
{"sensor": "aht10", "temp": 25.28, "humidity": 44.0}
```

For a loop, use:

```sh
mpremote connect auto exec "import temp_read; temp_read.run(count=0, interval_s=5)"
```

## Deployment

1. Create a board-local config file from the example:

   ```sh
   cp sps_pyb/flash/config.py.example sps_pyb/flash/config.py
   ```

2. Edit `sps_pyb/flash/config.py` with your Wi-Fi and MQTT values.

   `sps_pyb/flash/config.py` is git-ignored, so you can keep board-specific secrets there without committing them.

3. Deploy to the board with the host-side helper:

   ```sh
   chmod +x sps_pyb/deploy.sh
   ./sps_pyb/deploy.sh
   ```

   That script:

   - uploads files into `:/flash/...`, not `:/flash/flash/...`
   - creates `/flash/SKIPSD`
   - skips `__pycache__` and `config.py.example`
   - uploads `sps_pyb/flash/config.py` if it exists
   - can remove an old mistaken nested tree with `--clean-stale`

4. Optional: remove a previous bad nested deploy:

   ```sh
   ./sps_pyb/deploy.sh --clean-stale
   ```

The deployment keeps code on `/flash`. If an SD card is inserted, `boot.py` mounts it at `/sd` and creates `/sd/history` plus `/sd/queue`.

## Mock MQTT Test

To test Wi-Fi and MQTT before wiring sensors, point the board at your broker/subscriber host in `sps_pyb/flash/config.py`:

```python
WIFI_SSID = "your-ssid"
WIFI_PASSWORD = "your-password"
MQTT_HOST = "192.168.0.67"
MQTT_PORT = 1883
MQTT_TOPIC = "airquality/sensor"
MQTT_CALIBRATION_TOPIC = ""
MOCK_PUBLISH_INTERVAL_S = 5
MOCK_PUBLISH_COUNT = 0
```

After syncing `sps_pyb/flash/` to the board, run the mock publisher:

```sh
mpremote connect auto exec "import mock_publish; mock_publish.run()"
```

It uses the same `WiFiManager` and `MQTTPublisher` as the real runtime, prints the assigned IP via `ifconfig()`, and publishes dummy `pm_1_0`, `pm_2_5`, `pm_4_0`, `pm_10_0`, `temp`, and `humidity` fields to `airquality/sensor`.

For a single test message instead of a loop:

```sh
mpremote connect auto exec "import mock_publish; mock_publish.run_once()"
```

## Local Test Run

The pure-logic tests run on the host:

```sh
python3 -m unittest discover -s sps_pyb/tests -q
```

## Notes

- Create `/flash/SKIPSD` before first boot with an SD card inserted. Without it, the pyboard may boot from `/sd` instead of `/flash`.
- If `/sd` is unavailable, the node still attempts live MQTT publishing but skips durable history and replay.
