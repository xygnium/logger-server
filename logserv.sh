#!/bin/bash
# Control logserv, the logger-server systemd system service.
#   ./logserv.sh install        install or update the service, start it, start at
#                               boot (re-run after the service file changes)
#   ./logserv.sh start          (re)start, printing only problems
#   ./logserv.sh start-verbose  (re)start, printing every message, until the
#                               next start or reboot
#   ./logserv.sh stop           stop
#   ./logserv.sh uninstall      stop the service and remove it (keeps the database)
#   ./logserv.sh status         running or not, mode, db file, and the last 20 lines of output
#   ./logserv.sh version        the version of udp_listener.py and of the running service
#   ./logserv.sh help           show this list
set -e
cd "$(dirname "$0")"
case "$1" in
install)
    sudo cp logger-server.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable logger-server
    sudo systemctl restart logger-server
    systemctl --no-pager status logger-server
    ;;
start)
    sudo rm -f /run/logserv.env
    sudo systemctl restart logger-server
    systemctl --no-pager status logger-server
    ;;
start-verbose)
    echo "LOGSERV_OPTS=--verbose" | sudo tee /run/logserv.env > /dev/null
    sudo systemctl restart logger-server
    systemctl --no-pager status logger-server
    ;;
stop)
    sudo systemctl stop logger-server
    echo "logserv stopped"
    ;;
uninstall)
    sudo systemctl disable --now logger-server
    sudo rm -f /etc/systemd/system/logger-server.service
    sudo systemctl daemon-reload
    echo "logserv uninstalled (~/logserv.sqlite kept)"
    ;;
status)
    systemctl --no-pager status logger-server || true
    pid=$(systemctl show -p MainPID --value logger-server)
    if [ "$pid" != 0 ]; then
        args=$(ps -o args= -p "$pid")
        case "$args" in *--verbose*) echo "mode: verbose" ;; *) echo "mode: normal" ;; esac
        db=$(echo "$args" | sed -n 's/.*--db \([^ ]*\).*/\1/p')
        echo "db: ${db:-none} $( [ -n "$db" ] && ls -lh "$db" 2>/dev/null | awk '{print "(" $5 ")"}')"
    fi
    journalctl -u logger-server -n 20 --no-pager
    ;;
version)
    file=$(./udp_listener.py --version)
    pid=$(systemctl show -p MainPID --value logger-server)
    running=none
    if [ "$pid" != 0 ]; then
        running=$(journalctl _PID="$pid" -o cat --no-pager | sed -n 's/^listening on .*, version //p' | tail -1)
    fi
    echo "file:    ${file}"
    echo "running: ${running:-unknown}"
    if [ "$running" != none ] && [ "$running" != "$file" ]; then
        echo "warning: the service isn't running this file's version; run ./logserv.sh install"
    fi
    ;;
help|-h|--help)
    sed -n '2,/^set -e/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
    ;;
*)
    sed -n '2,/^set -e/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
