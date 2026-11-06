#!/usr/bin/env python3
"""Listen for the data loggers' pushes and answer each one.

Usage:
    ./udp_listener.py              # listen on UDP 8080
    ./udp_listener.py --port 9000

Prints each message with a GOOD/OK/BAD/FAULT verdict, this host's local arrival
time and the sender, and replies "ack <UTC time>" so the logger can later
check its clock against this host. Stop with Ctrl-C.

The verdict is the server's judgement; the logger only reports numbers.
For a hello line:
    BAD   pushes were missed (seq skipped), or rssi below RSSI_BAD
    OK    rssi below RSSI_OK, WiFi reconnected, or the logger restarted
    GOOD  otherwise
A fault line ("fault <source>=<reason> ...": the logger is in a hard fault
and has stopped normal work) is FAULT. Any other message that isn't a
parseable hello line is BAD.
"""

import argparse
import datetime
import socket

RSSI_OK = -70   # dBm; weaker than this is OK, not GOOD
RSSI_BAD = -80  # dBm; weaker than this is BAD


def parse_hello(text):
    """Return the key=value fields of a hello line, or None."""
    words = text.strip().split()
    if not words or words[0] != "hello":
        return None
    fields = dict(w.split("=", 1) for w in words[1:] if "=" in w)
    try:
        for key in ("seq", "up", "rssi", "reconnects"):
            fields[key] = int(fields[key])
    except (KeyError, ValueError):
        return None
    return fields


def judge(fields, prev):
    """Return GOOD, OK or BAD for a hello, given the logger's previous one."""
    if fields is None:
        return "BAD"
    restarted = prev is not None and (
        fields["seq"] <= prev["seq"] or fields["up"] < prev["up"])
    if prev is not None and not restarted and fields["seq"] != prev["seq"] + 1:
        return "BAD"
    if fields["rssi"] < RSSI_BAD:
        return "BAD"
    if fields["rssi"] < RSSI_OK or restarted:
        return "OK"
    if prev is not None and fields["reconnects"] > prev["reconnects"]:
        return "OK"
    return "GOOD"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    print(f"listening on UDP {args.port}", flush=True)

    last = {}  # logger MAC (or sender IP) -> its previous hello fields
    while True:
        data, addr = sock.recvfrom(1024)
        now = datetime.datetime.now()
        text = data.decode("ascii", errors="replace")
        fields = parse_hello(text)
        key = fields.get("mac", addr[0]) if fields else None
        if text.startswith("fault "):
            verdict = "FAULT"
        else:
            verdict = judge(fields, last.get(key))
        if fields:
            last[key] = fields
        print(f"{verdict:<5} {now:%H:%M:%S} {addr[0]}:{addr[1]} {text}",
              flush=True)
        utc = datetime.datetime.now(datetime.timezone.utc)
        sock.sendto(f"ack {utc:%Y-%m-%dT%H:%M:%SZ}".encode(), addr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
