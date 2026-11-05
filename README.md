# logger-server

The host-side server for the data loggers. Each logger pushes its readings over UDP; this server acks each push and will store the readings in SQLite.

| Logger | Firmware | Notes |
|---|---|---|
| ambient (outdoor air) | `esp32-dev/ambient` | Pushes a status line; no sensor readings yet |
| attic | `pico-dev/temp-sense` | Currently listens and is polled; likely to change to push like ambient |

The message formats are in [PROTOCOL.md](PROTOCOL.md). It is the shared reference for both firmware repos.

## Running

```bash
./udp_listener.py              # listen on UDP 8080
./udp_listener.py --port 9000
```

It prints each message with its arrival time and sender, and replies `ack <UTC time>`. It doesn't store anything yet.

## Status

- `udp_listener.py`, moved from `esp32-dev/ambient`, unchanged apart from its docstring.
- Not yet written: SQLite storage.

## Decided

- Storage is SQLite on this host, not MariaDB, with the data kept forever. With one row per reading that's roughly 100 to 150 MB a year for ambient at 120 s (estimated), so a few GB over decades. Back up with SQLite's `.backup`, not a plain file copy.
- No MQTT for now.
- One database file. One row per reading, in snake_case:

  ```
  readings: id, logger_id, timestamp, sensor, data_type, value, status
  loggers:  logger_id, mac, name, location
  index:    (logger_id, data_type, timestamp)
  ```

  `timestamp` is the reading's own UTC time. `data_type` names the measured quantity with its unit, such as `temperature_C`, `humidity_pct` or `pressure_hPa`. `status` is OK or fail. Operations select by time range, and readings from different loggers aren't time-aligned.
- The loggers push and never listen.

## Open

- Whether each push carries every sample since the last ack, so the database fills its own gaps, or only the latest.
- Remote commands: proposed to ride in the ack (`esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
- Which host runs it, and how it's kept running.
