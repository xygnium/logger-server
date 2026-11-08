#!/bin/bash
# Control logserv, the logger-server systemd user service.
#   ./logserv.sh install   install or update the service, start it, start at boot
#                          (re-run after the service file changes)
#   ./logserv.sh start
#   ./logserv.sh stop
#   ./logserv.sh status    running or not, and the last 20 lines of output
set -e
cd "$(dirname "$0")"
case "$1" in
install)
    mkdir -p ~/.config/systemd/user
    cp logger-server.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable logger-server
    systemctl --user restart logger-server
    sudo loginctl enable-linger "$USER"     # start at boot, without a login
    systemctl --user --no-pager status logger-server
    ;;
start)
    systemctl --user start logger-server
    systemctl --user --no-pager status logger-server
    ;;
stop)
    systemctl --user stop logger-server
    echo "logserv stopped"
    ;;
status)
    systemctl --user --no-pager status logger-server || true
    journalctl --user -u logger-server -n 20 --no-pager
    ;;
*)
    echo "usage: $0 install|start|stop|status"
    exit 1
    ;;
esac
