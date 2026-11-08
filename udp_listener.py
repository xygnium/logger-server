#!/usr/bin/env python3
"""Listen for the logger's messages, store them and ack each one.

Usage:
    ./udp_listener.py                        # listen on UDP 8080
    ./udp_listener.py --port 9000
    ./udp_listener.py --db readings.sqlite   # also store them

The logger sends one message at a time and resends it until it's acked:
    data <timestamp,sensor,data_type,value,status>
    event <timestamp,source,event,detail>
Each is printed with this host's local arrival time, stored (with --db) in
the readings or events table, and answered with "ack <UTC time, ms>" so the
logger can check its clock. A message the same as the one before (resent
because an ack was lost) isn't stored again; it becomes an event of our own,
logserv,repeat,<message>. Stop with Ctrl-C.
"""

import argparse
import datetime
import socket
import sqlite3


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
    """Store a data or event message. Anything else is ignored."""
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
        return
    db.commit()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--db", help="SQLite file to store readings and events in")
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
        text = data.decode("ascii", errors="replace").strip()
        if text == last:
            # Resent because our ack was lost: not stored again; logged as
            # logserv's own event instead.
            text = f"event {utc:%Y-%m-%dT%H:%M:%S}.{ms:03d}Z,logserv,repeat,{text}"
        else:
            last = text
        print(f"{now:%H:%M:%S} {text}", flush=True)
        if db:
            store(db, text)
        sock.sendto(f"ack {utc:%Y-%m-%dT%H:%M:%S}.{ms:03d}Z".encode(), addr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
