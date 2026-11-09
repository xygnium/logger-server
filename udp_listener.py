#!/usr/bin/env python3
"""Listen for the logger's messages, store them and ack each one.

Usage:
    ./udp_listener.py                        # listen on UDP 8080
    ./udp_listener.py --port 9000
    ./udp_listener.py --db readings.sqlite   # also store them
    ./udp_listener.py --verbose              # print every message

The logger sends one message at a time and resends it until it's acked:
    data <timestamp,sensor,data_type,value,status>
    event <timestamp,source,event,detail>
Each is stored (with --db) in the readings or events table and answered with
"ack <UTC time, ms> <CRC-16 of the message as received, 4 hex digits>"
(CRC-16/XMODEM):
the CRC tells the logger its message arrived intact, and the time lets it
check its clock. A message already stored (resent because an ack was lost,
or after a logger reboot) isn't stored again, and is printed as
"repeat <message>". A reading is the same when its timestamp, sensor and
data_type match; an event, when all four fields match.

Output, each line with this host's local arrival time: normally only
repeats and messages that can't be stored (not data or event, or the wrong
number of fields); with --verbose, every message. Stop with Ctrl-C.
"""

import argparse
import datetime
import socket
import sqlite3
import binascii

# Raise by one with every change to this file.
VERSION = 1


def open_db(path):
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY,
        timestamp TEXT, sensor TEXT, data_type TEXT, value REAL, status TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        timestamp TEXT, source TEXT, event TEXT, detail TEXT)""")
    # A resent message is ignored (INSERT OR IGNORE). This fails if the
    # database already holds duplicates.
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS readings_key"
               " ON readings (timestamp, sensor, data_type)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS events_key"
               " ON events (timestamp, source, event, detail)")
    return db


def store(db, text):
    """Store a data or event message. False if it was already stored. Raises
    ValueError for anything else."""
    kind, _, row = text.strip().partition(" ")
    if kind == "data":
        ts, sensor, data_type, value, status = row.split(",")
        cur = db.execute("INSERT OR IGNORE INTO readings (timestamp, sensor, data_type, value, status)"
                   " VALUES (?,?,?,?,?)",
                   (ts, sensor, data_type, float(value) if value else None, status))
    elif kind == "event":
        ts, source, event, detail = row.split(",", 3)
        cur = db.execute("INSERT OR IGNORE INTO events (timestamp, source, event, detail)"
                   " VALUES (?,?,?,?)", (ts or None, source, event, detail))
    else:
        raise ValueError("not a data or event message")
    db.commit()
    return cur.rowcount == 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--db", help="SQLite file to store readings and events in")
    ap.add_argument("--verbose", action="store_true", help="print every message")
    ap.add_argument("--version", action="version", version=str(VERSION))
    args = ap.parse_args()

    db = open_db(args.db) if args.db else None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    print(f"listening on UDP {args.port}, version {VERSION}", flush=True)

    while True:
        data, addr = sock.recvfrom(1024)
        now = datetime.datetime.now()
        utc = datetime.datetime.now(datetime.timezone.utc)
        ms = utc.microsecond // 1000
        crc = binascii.crc_hqx(data, 0)
        text = data.decode("ascii", errors="replace").strip()
        store_text = text
        try:
            if db:
                if not store(db, text):
                    # Already stored: resent because our ack was lost, or
                    # after a logger reboot.
                    store_text = f"repeat {text}"
            elif text.partition(" ")[0] not in ("data", "event"):
                raise ValueError("not a data or event message")
            problem = None
        except ValueError as e:
            problem = e
        if args.verbose or store_text != text or problem:
            print(f"{now:%H:%M:%S} {store_text}"
                  + (f"  [not stored: {problem}]" if problem else ""), flush=True)
        # The ack's time is read just before sending, after the store, so it
        # is the time the ack leaves.
        utc = datetime.datetime.now(datetime.timezone.utc)
        ms = utc.microsecond // 1000
        sock.sendto(f"ack {utc:%Y-%m-%dT%H:%M:%S}.{ms:03d}Z {crc:04x}".encode(), addr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
