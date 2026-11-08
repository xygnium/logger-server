# Logger protocol

What the loggers and the server send each other over UDP.

## Current: ambient (`esp32-dev/ambient`)

The logger sends one message at a time to the server (UDP 8080) and waits for its ack before sending the next. Each message is one ASCII line:

```
data <timestamp>,<sensor>,<data_type>,<value>,<status>
event <timestamp>,<source>,<event>,<detail>
```

- `data` is one reading, e.g. `data 2026-11-07T13:35:48.153Z,sht45,rh_pct,54.00,ok`. A failed reading has an empty value and the reason as the status.
- `event` is one event, e.g. `event 2026-11-07T13:35:48.153Z,sht45,fail,nack`. The timestamp is empty for an event from before the logger's clock is set.
- Events go ahead of readings.

The server replies to the sender's address and port:

```
ack <UTC time as YYYY-MM-DDTHH:MM:SS.mmmZ> <CRC-16 of the message, 4 hex digits>
```

- **CRC:** CRC-16/XMODEM of the message as received (Python `binascii.crc_hqx(data, 0)`; ESP32 `esp_rom_crc16_be` from the ROM). A reply without the matching CRC isn't an ack; the logger prints `expected ack failed`.
- **Time:** read just before the ack is sent. The logger takes it plus half the round trip as the true time, and with `clock auto` corrects its DS3231 when that's more than 50 ms off. The server's clock must be accurate (dev10's is internet-synced).
- **No ack within 2 s:** the logger sends the same message again every 10 s, forever, until it's acked.
- **Repeats:** a message the same as the one before (resent because an ack was lost) is acked but not stored again; the server stores its own event instead, `logserv,repeat,<message>`.

The whole system, and why one row per value, is in `esp32-dev/ambient/SYSTEM.md`.

## Current: attic (`pico-dev/temp-sense`)

This is the opposite model: the Pico W listens on UDP 8080, and `udp_client.py` polls it. `read` returns one line per DS18B20, keyed by ROM id. `settime YYYY-MM-DD HH:MM:SS D` sets its DS3231. Any other command gets a generic ack. It is likely to change to sending, like ambient.

## Open

- Commands in the ack (proposed in `esp32-dev/ambient/FIRMWARE.md`, "Remote commands").
