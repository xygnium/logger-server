# Alerting (proposal, set aside)

Set aside 2026-11-09: alerting is a general need for all the loggers and controllers, not just ambient, and existing tools may do it. Look at these before building anything:

- **Healthchecks.io** (hosted or self-hosted): a dead man's switch. Something pings a URL; when the pings stop, it alerts. Covers silence for any device, and dev10 down too if hosted.
- **Uptime Kuma** (self-hosted): monitors with a dashboard; push monitors for silence, HTTP and port checks; alerts to ntfy, email, Telegram and others.
- **Grafana:** graphs of the readings plus alert rules on the data (SQLite needs a plugin). Bigger, but also gives charts.
- **Home Assistant / Node-RED:** if one is already in use.

These cover silence; event alerts (`sht45 fail` and so on) would still need a small hook, except with Grafana, which reads the data itself.

The rest of this file is the original proposal: a small script of our own. Nothing is built or decided.

This proposes how to get told when the ambient logger has a problem, without checking the console or the database.

## What to alert on

**Table 1: Alerts**

| Condition | How it's seen | Alert |
|---|---|---|
| Logger silent: no message for 10 min | The newest row in the database is old | Yes, once when it starts and once when messages return |
| `sd,fault` or `rtc,fault` | Event | Yes: sampling has stopped until a reboot |
| Sensor `fail` / `recover` | Event | Yes. The logger logs `fail` once per reason, so this doesn't flood |
| `supply,low` / `recovered` | Event | Yes |
| `clock,unset` | Event | Yes: no sampling until an ack sets the clock |
| `logger,boot` | Event | Yes: an unexpected reboot points to power or a crash. Also on every flash, and when opening the serial port resets the board |
| `clock,corrected` / `stepped` / `set` | Event | No, these are normal |

Silence covers the logger dead or unpowered, its WiFi down, and logserv itself stopped, since in each case no rows arrive. A 10 min limit works at a 30 s or 2 min sample interval.

## How it would work

A separate script, `alert.py`, run every 5 minutes by a systemd timer on dev10. Each run:

1. Reads the newest row's arrival time. If it's over 10 minutes ago and no silence alert has gone out yet, it sends one. When rows return, it sends "back".
2. Reads the events with an id above the last one it handled, and sends one alert for each event marked Yes in Table 1. Each alert gives the event's own time as well as when it arrived, since after an outage the logger sends its backlog from the card and events can arrive hours late: "sht45 fail nack at 14:02Z (received 15:30)".
3. Saves the last event id and the silence state in a small state file.

On its first run (no state file) it starts from the newest event id and sends nothing; otherwise every event already in the database would alert at once.

Why a separate script and not inside `udp_listener.py`: it keeps working when the listener has stopped, and the listener stays as it is. The cost is up to 5 minutes' delay, which is fine here, since nothing on the logger needs a faster response.

The database stores the logger's timestamp, not the arrival time. Silence can be judged by the newest logger timestamp (the logger's clock is kept within 50 ms), so no schema change is needed. After an outage the backlog goes oldest first, so "back" is sent only once the logger has caught up: about 10 minutes per day of outage.

## How to be told

**Table 2: Notification options**

| Option | Setup | Pros | Cons |
|---|---|---|---|
| **ntfy** (ntfy.sh, recommended) | Install the phone app, subscribe to a topic; the script makes one HTTP POST | Free, no account, a push to the phone within seconds, about 3 lines of code | Anyone who knows the topic name can read it: use a long random name. Depends on the ntfy.sh service (it can be self-hosted later) |
| Email (Gmail SMTP) | A Gmail app password, stored on dev10 | No new app; Python's standard library | Slower and easy to miss; a password on dev10 |
| Pushover | A one-off $5 app; an API key | Reliable, quiet hours | Paid, account needed |
| Telegram bot | Create a bot, get a chat id | Free | More setup |

## Not covered

- dev10 down, or its internet down: no alerts at all. Accepted for rev 1. A check from outside (for example a free uptime service pinging dev10) could be added later.
- Readings with `status` not `ok` are covered by the sensor `fail` event, not checked row by row.
- Card nearly full: there's no warning yet (no `sd low` event). A full card alerts as `sd,fault,write_failed`, but only once sampling has stopped.

## Managing it

Through `logserv.sh`, like logserv:

| Command | Alerting |
|---|---|
| `./logserv.sh install` | Also installs `alert.service` and `alert.timer` and starts the timer |
| `./logserv.sh status` | Also shows the timer's last and next run and the last few lines of alert output |
| `./logserv.sh stop` / `start` | Also stops / starts the alerts |
| `./logserv.sh uninstall` | Also removes them (keeps the state file) |
| `./logserv.sh version` | Also shows `alert.py`'s version. Each run uses the file as it is, so there's no separate running version |
| `./logserv.sh help` | Lists these, alerting included |

- `alert.py` runs once and exits; systemd starts it every 5 min. Its output goes to the journal.
- `alert.py` has a version number (`VERSION`), raised by one with every change, and `--version`, like `udp_listener.py`.
- `./alert.py --help` lists its options; `./alert.py --test` sends one test alert, to check the channel.
- State: `~/alert.state` (last event id, silence on/off).

## Work

- `alert.py`, about 60 lines, standard library only.
- `alert.service` and `alert.timer`; `logserv.sh install` installs them too.
- Docs: README, SYSTEM.md.

## Test

1. Unplug the logger: a silence alert within 15 minutes. Plug it back in: a `boot` alert and "back".
2. Unplug a sensor cable for one sample: a `fail` alert, then a `recover` alert.
3. Stop logserv (`./logserv.sh stop`): a silence alert. Start it again: "back".

## To decide

1. The notification channel (Table 2).
2. Which events alert (Table 1).
3. The silence limit (10 min) and the check interval (5 min).
4. `boot` alerts while working on the board: accept them, or add a mute switch (for example, no alerts while a file `~/alert.mute` exists).
