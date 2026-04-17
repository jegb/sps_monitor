# `sps_pyb`

MicroPython port of the sensor node for the `pybd-sf6w`.

This target intentionally keeps only the device-side responsibilities:

- read `SPS30`
- read `SHT3x`
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

## Deployment

1. Create a board-local config file from the example:

   ```sh
   cp sps_pyb/flash/config.py.example sps_pyb/flash/config.py
   ```

2. Edit `sps_pyb/flash/config.py` with your Wi-Fi and MQTT values.

3. Create the remote directories on the board and pin boot to internal flash:

   ```sh
   mpremote connect auto exec "open('/flash/SKIPSD', 'a').close()"
   mpremote connect auto fs mkdir :lib
   mpremote connect auto fs mkdir :lib/app
   mpremote connect auto fs mkdir :lib/sensors
   mpremote connect auto fs mkdir :lib/umqtt
   ```

4. Copy the files from this repo onto the board:

   ```sh
   find sps_pyb/flash -type f | while read -r file; do
     rel=${file#sps_pyb/flash/}
     mpremote connect auto fs cp "$file" ":$rel"
   done
   ```

5. Reset the board:

   ```sh
   mpremote connect auto reset
   ```

The deployment keeps code on `/flash`. If an SD card is inserted, `boot.py` mounts it at `/sd` and creates `/sd/history` plus `/sd/queue`.

## Local Test Run

The pure-logic tests run on the host:

```sh
python3 -m unittest discover -s sps_pyb/tests -q
```

## Notes

- Create `/flash/SKIPSD` before first boot with an SD card inserted. Without it, the pyboard may boot from `/sd` instead of `/flash`.
- If `/sd` is unavailable, the node still attempts live MQTT publishing but skips durable history and replay.
