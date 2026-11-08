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
check its clock. A message the same as the one before (resent
because an ack was lost) isn't stored again; it becomes an event of our own,
logserv,repeat,<message>.

Output, each line with this host's local arrival time: normally only
repeats and messages that can't be stored (not data or event, or the wrong
number of fields); with --verbose, every message. Stop with Ctrl-C.
"""

import argparse
import datetime
import socket
import sqlite3
import binascii


def open_db(path):
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY,
        timestamp TEXT, sensor TEXT, data_type TEXT, value REAL, status TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY,
        timestamp TEXT, source TEXT, event TEXT, detail TEXT)""")
    return db


def store(db, text):
    """Store a data or event message. Raises ValueError for anything else."""
    kind, _, row = text.strip().partition(" ")
    if kind == "data":
        ts, sensor, data_type, value, status = row.split(",")
        db.execute("INSERT INTO readings (timestamp, sensor, data_type, value, status)"
                   " VALUES (?,?,?,?,?)",
                   (ts, sensor, data_type, float(value) if value else None, status))
    elif kind == "event":
        ts, source, event, detail = row.split(",", 3)
        db.execute("INSERT INTO events (timestamp, source, event, detail)"
                   " VALUES (?,?,?,?)", (ts or None, source, event, detail))
    else:
        raise ValueError("not a data or event message")
    db.commit()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--db", help="SQLite file to store readings and events in")
    ap.add_argument("--verbose", action="store_true", help="print every message")
    args = ap.parse_args()

    db = open_db(args.db) if args.db else None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    print(f"listening on UDP {args.port}", flush=True)

    last = None
    while True:
        data, addr = sock.recvfrom(1024)
        now = datetime.datetime.now()
        utc = datetime.datetime.now(datetime.timezone.utc)
        ms = utc.microsecond // 1000
        crc = binascii.crc_hqx(data, 0)
        text = data.decode("ascii", errors="replace").strip()
        if text == last:
            # Resent because our ack was lost: not stored again; logged as
            # logserv's own event instead.
            store_text = f"event {utc:%Y-%m-%dT%H:%M:%S}.{ms:03d}Z,logserv,repeat,{text}"
        else:
            last = text
            store_text = text
        try:
            if db:
                store(db, store_text)
            elif store_text.partition(" ")[0] not in ("data", "event"):
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
