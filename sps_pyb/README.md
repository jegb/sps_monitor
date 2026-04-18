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
