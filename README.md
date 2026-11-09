# logger-server

The host-side server for the data loggers (logserv). The ambient logger sends each reading and event over UDP; this server acks each one and stores it in SQLite.

| Logger | Firmware | Notes |
|---|---|---|
| ambient (outdoor air) | `esp32-dev/ambient` | Sends each reading and event, one at a time until acked |
| attic | `pico-dev/temp-sense` | Currently listens and is polled; likely to change to sending like ambient |

The message formats are in [PROTOCOL.md](PROTOCOL.md). It is the shared reference for both firmware repos.

To test the link with the ambient logger, see [TEST-AMBIENT.md](TEST-AMBIENT.md).

## Running

```bash
./udp_listener.py                       # listen on UDP 8080, ack, don't store
./udp_listener.py --db ~/logserv.sqlite # also store
./udp_listener.py --port 9000
./udp_listener.py --verbose             # print every message
```

`udp_listener.py` has a version number (`VERSION`), raised by one with every change to it; `--version` prints it. By default it prints only repeats and messages it can't store; `--verbose` prints every message. The rest is in the `udp_listener.py` docstring.

### As a service on dev10

`logger-server.service` runs it as a systemd system service, as user `mike`, storing to `~/logserv.sqlite`. It starts at boot and restarts after a crash. It assumes the repo is cloned at `~/dev/github/logger-server`; edit the file if not. Stop any `udp_listener.py` started by hand first, since only one program can hold port 8080.

```bash
./logserv.sh install     # install or update the service and (re)start it; also after a git pull
./logserv.sh status      # running or not, and the last 20 lines of output
./logserv.sh version     # the file's version and the running service's; warns if they differ
./logserv.sh stop
./logserv.sh start
./logserv.sh uninstall   # keeps the database
```

### Database

Two tables, one row per reading or event:

```
readings: id, timestamp, sensor, data_type, value, status
events:   id, timestamp, source, event, detail
```

`timestamp` is the logger's own UTC time with milliseconds, like `2026-11-06T07:10:00.137Z`. `data_type` names the quantity with its unit: `temp_c`, `rh_pct`, `ratio`, `pressure_pa`. `status` is `ok` or the failure reason, with an empty value. Back up with SQLite's `.backup`, not a plain file copy:

```bash
sqlite3 ~/logserv.sqlite ".backup ~/logserv-backup.sqlite"
```

`./logdb.sh` shows the newest readings and events, the readings in the last few minutes, and the failed readings; `./logdb.sh help` lists the commands.

## Decided

- Storage is SQLite on this host, not MariaDB, with the data kept forever. With one row per reading that's roughly 100 to 150 MB a year for ambient at 120 s (estimated), so a few GB over decades.
- No MQTT for now.
- One database file, one row per reading (see Database). No logger id: there is one ESP32.
- The loggers send and never listen.
- The server runs on dev10 to start with, as a systemd system service.

## Open

- Readings lost from the logger's RAM queue (reboot, or a full queue) are only on its SD card; nothing copies them over yet.
- Remote commands: proposed to ride in the ack (`esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
