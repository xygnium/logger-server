#!/bin/bash
# Control logserv, the logger-server systemd system service.
#   ./logserv.sh install   install or update the service, start it, start at boot
#                          (re-run after the service file changes)
#   ./logserv.sh start
#   ./logserv.sh stop
#   ./logserv.sh uninstall stop the service and remove it (keeps the database)
#   ./logserv.sh status    running or not, and the last 20 lines of output
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
    sudo systemctl start logger-server
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
    journalctl -u logger-server -n 20 --no-pager
    ;;
*)
    echo "usage: $0 install|uninstall|start|stop|status"
    exit 1
    ;;
esac
