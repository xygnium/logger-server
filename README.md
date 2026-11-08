# logger-server

The host-side server for the data loggers. Each logger pushes its readings over UDP; this server acks each push and will store the readings in SQLite.

| Logger | Firmware | Notes |
|---|---|---|
| ambient (outdoor air) | `esp32-dev/ambient` | Pushes a status line; no sensor readings yet |
| attic | `pico-dev/temp-sense` | Currently listens and is polled; likely to change to push like ambient |

The message formats are in [PROTOCOL.md](PROTOCOL.md). It is the shared reference for both firmware repos.

To test the link with the ambient logger, see [TEST-AMBIENT.md](TEST-AMBIENT.md).

## Running

```bash
./udp_listener.py              # listen on UDP 8080
./udp_listener.py --port 9000
./udp_listener.py --verbose    # print every message
```

By default it prints only repeats and messages it can't store; `--verbose` prints every message. The rest is in the `udp_listener.py` docstring.

### As a service on dev10

`logger-server.service` runs it as a systemd system service, as user `mike`, which starts at boot and restarts after a crash. It assumes the repo is cloned at `~/dev/github/logger-server`; edit the file if not. Stop any `udp_listener.py` started by hand first, since only one program can hold port 8080.

```bash
sudo cp logger-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now logger-server
journalctl -u logger-server -f        # watch the output
```

After editing the file, repeat the `cp` and `daemon-reload`, then `sudo systemctl restart logger-server`. `logserv.sh install` does all of this.

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

  `timestamp` is the reading's own UTC time, with milliseconds, like `2026-11-06T07:10:00.137Z`. `data_type` names the measured quantity with its unit, such as `temperature_C`, `humidity_pct` or `pressure_hPa`. `status` is OK or fail. Operations select by time range, and readings from different loggers aren't time-aligned.
- The loggers push and never listen.
- The server runs on dev10 to start with, as a systemd system service.

## Open

- Whether each push carries every sample since the last ack, so the database fills its own gaps, or only the latest.
- Remote commands: proposed to ride in the ack (`esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
