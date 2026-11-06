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
```

It prints each message with a GOOD/OK/BAD/FAULT verdict, its arrival time and sender, and replies `ack <UTC time>`. The verdict is the server's judgement, not the logger's: BAD if pushes were missed (a gap in `seq`), rssi is below -80 dBm, or the message isn't a hello line (FAULT for a fault line instead: the logger is in a hard fault); OK if rssi is below -70 dBm, WiFi reconnected, or the logger restarted; GOOD otherwise. The rules are in the `udp_listener.py` docstring. It doesn't store anything yet.

### As a service on dev10

`logger-server.service` runs it as a systemd user service, which starts at boot and restarts after a crash. It assumes the repo is cloned at `~/dev/github/logger-server`; edit the paths in the file if not. Stop any `udp_listener.py` started by hand first, since only one program can hold port 8080.

```bash
mkdir -p ~/.config/systemd/user
cp logger-server.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now logger-server
sudo loginctl enable-linger $USER     # start at boot, without a login
journalctl --user -u logger-server -f # watch the output
```

After editing the copy in `~/.config/systemd/user/`, run `systemctl --user daemon-reload` and `systemctl --user restart logger-server`.

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
- The server runs on dev10 to start with, as a systemd user service.

## Open

- Whether each push carries every sample since the last ack, so the database fills its own gaps, or only the latest.
- Remote commands: proposed to ride in the ack (`esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
