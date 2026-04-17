# `pizerow`

Thin Raspberry Pi Zero / Zero 2W sensor node for `sps_monitor`.

This subtree keeps only the device-side work:

- read `SPS30`
- read `SHT3x`
- publish raw MQTT payloads to `airquality/sensor`
- store lightweight local CSV history
- store a local JSONL replay queue when MQTT is unavailable

It does not include Flask, SQLite, dashboard code, or aggregate calculation.

## Layout

```text
pizerow/
  README.md
  requirements.txt
  config.py.example
  main.py
  app/
  sensors/
  tests/
```

## MQTT Contract

The Pi Zero node publishes only the raw live fields:

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

Topic: `airquality/sensor`

## Dependencies

```sh
python3 -m pip install -r pizerow/requirements.txt
```

The `pizerow` target uses `smbus2` for both sensors and `paho-mqtt` for publishing. It does not require Blinka.

## Quick Setup

On a Raspberry Pi Zero / Zero 2W, the fastest path is:

```sh
chmod +x pizerow/setup.sh
./pizerow/setup.sh
```

That script:

- installs the minimal apt packages for the thin node
- installs `mosquitto-clients` for MQTT diagnostics with `mosquitto_pub` and `mosquitto_sub`
- creates `pizerow/.venv`
- installs `pizerow/requirements.txt`
- creates `pizerow/config.py` if missing
- creates `pizerow/data/history` and `pizerow/data/queue`
- runs the host-side unit tests

## Configuration

Create a local config file:

```sh
cp pizerow/config.py.example pizerow/config.py
```

Edit:

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_TOPIC`
- `MQTT_CLIENT_ID`
- `I2C_BUS`
- `SPS30_ADDR`
- `SHT3X_ENABLED`
- `SHT3X_ADDR`
- optionally `DATA_DIR`

By default the node stores local files under `pizerow/data/`.

## Run

Enable I2C on the Pi if it is not already enabled, then start the node:

```sh
python3 -m pizerow.main
```

## Auto-Start On Boot

Install the `systemd` unit from this repo:

```sh
chmod +x pizerow/install_service.sh
sudo ./pizerow/install_service.sh
```

That creates `/etc/systemd/system/pizerow.service` with the correct absolute paths for the current clone, enables it, and starts it immediately.

Useful commands:

```sh
systemctl status pizerow
sudo journalctl -u pizerow -f
sudo systemctl restart pizerow
sudo systemctl disable --now pizerow
```

The runtime behavior is:

1. Replay any queued MQTT records from the local queue.
2. Read SPS30 and optional SHT3x.
3. Append the sample to a daily CSV file.
4. Publish the raw payload to MQTT.
5. Queue the record if publish fails.

## Local Storage

- history files: `data/history/YYYY-MM-DD.csv`
- replay queue: `data/queue/pending.jsonl`
- queue checkpoint: `data/queue/state.json`

## Local Test Run

```sh
python3 -m unittest discover -s pizerow/tests -q
```

## Notes

- Linux should keep system time synced already; this target does not do board-local NTP management.
- If MQTT is disabled, the node still writes local CSV history.
- If the broker is down, samples are retained locally and replayed in order on the next successful publish cycle.
