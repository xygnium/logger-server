# Alerting (proposal)

Not built, and nothing is decided yet. This proposes how to get told when the ambient logger has a problem, without checking the console or the database.

## What to alert on

**Table 1: Alerts**

| Condition | How it's seen | Alert |
|---|---|---|
| Logger silent: no message for 10 min | The newest row in the database is old | Yes, once when it starts and once when messages return |
| `sd,fault` or `rtc,fault` | Event | Yes: sampling has stopped until a reboot |
| Sensor `fail` / `recover` | Event | Yes. The logger logs `fail` once per reason, so this doesn't flood |
| `supply,low` / `recovered` | Event | Yes |
| `clock,unset` | Event | Yes: no sampling until an ack sets the clock |
| `logger,boot` | Event | Yes: an unexpected reboot points to power or a crash |
| `clock,corrected` / `stepped` / `set` | Event | No, these are normal |

Silence covers the logger dead or unpowered, its WiFi down, and logserv itself stopped, since in each case no rows arrive. A 10 min limit works at a 30 s or 2 min sample interval.

## How it would work

A separate script, `alert.py`, run every 5 minutes by a systemd timer on dev10. Each run:

1. Reads the newest row's arrival time. If it's over 10 minutes ago and no silence alert has gone out yet, it sends one. When rows return, it sends "back".
2. Reads the events with an id above the last one it handled, and sends one alert for each event marked Yes in Table 1.
3. Saves the last event id and the silence state in a small state file.

Why a separate script and not inside `udp_listener.py`: it keeps working when the listener has stopped, and the listener stays as it is. The cost is up to 5 minutes' delay, which is fine here, since nothing on the logger needs a faster response.

The database stores the logger's timestamp, not the arrival time. Silence can be judged by the newest logger timestamp (the logger's clock is kept within 50 ms), so no schema change is needed.

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
