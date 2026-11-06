# Logger protocol

What the loggers and the server send each other over UDP. This records the current state. The sample format isn't designed yet.

## Current: ambient (`esp32-dev/ambient`)

The logger pushes one datagram to the server (default port 8080) at boot and then every push interval. It is ASCII, a single line of `key=value` fields after the word `hello`:

```
hello seq=<count> up=<seconds since boot> rssi=<dBm> ap=<access point MAC> ip=<own address> mac=<own MAC> reconnects=<times WiFi was regained> push_s=<interval> vin_mv=<supply voltage, mV; 0 if unavailable>
```

The server replies to the sender's address and port:

```
ack <UTC time as YYYY-MM-DDTHH:MM:SSZ>
```

The logger waits 2 s for the ack. A missing ack is counted and logged, and nothing is resent. The ack time is meant for checking the logger's clock (the `clock auto` or `clock report` setting).

### Fault line

While the logger is in a hard fault it sends this in place of the status line, at once when the fault is raised and then every push interval, until it is rebooted:

```
fault sd=<missing|mount_failed|not_responding> seq=<n> up=<seconds since boot> mac=<own MAC>
```

The server acks it like any other message.

## Current: attic (`pico-dev/temp-sense`)

This is the opposite model: the Pico W listens on UDP 8080, and `udp_client.py` polls it. `read` returns one line per DS18B20, keyed by ROM id. `settime YYYY-MM-DD HH:MM:SS D` sets its DS3231. Any other command gets a generic ack. It is likely to change to push, like ambient.

## To design

- The sample message: fields per logger, a sample timestamp from the logger's RTC, and per-sensor OK or fail flags.
- Logger identity: the MAC already in the ambient line, or a name setting.
- Backlog: whether a push carries every sample since the last acked one.
- Commands in the ack (proposed in `esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
