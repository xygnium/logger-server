#!/bin/bash
# Look at logserv's database. ./logdb.sh help lists the commands.
DB="${LOGSERV_DB:-$HOME/logserv.sqlite}"
q() { sqlite3 -header -column "$DB" "$1"; }
case "$1" in
latest)
    q "select timestamp, sensor, data_type, value, status from readings order by id desc limit ${2:-6}"
    ;;
count)
    q "select count(*) as rows from readings where timestamp > strftime('%Y-%m-%dT%H:%M:%SZ','now','-${2:-10} minutes')"
    ;;
events)
    q "select timestamp, source, event, detail from events order by id desc limit ${2:-10}"
    ;;
bad)
    q "select timestamp, sensor, data_type, status from readings where status != 'ok' order by id desc limit ${2:-10}"
    ;;
help|*)
    cat <<USAGE
usage: $0 <command> [n]     database: $DB (set LOGSERV_DB to change)
  latest [n]    newest n readings (6, one sample); the newest should be no older than one sample interval
  count [min]   readings in the last min minutes (10); 6 per sample, so 120 at 30 s, 30 at 2 min
  events [n]    newest n events (10): boots, sensor failures, clock corrections
  bad [n]       newest n readings that aren't ok (10)
  help          this list
USAGE
    [ "$1" = help ] || [ -z "$1" ]
    ;;
esac
