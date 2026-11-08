# Test: ambient logger to logger-server

Checks the link: the ambient logger sends each reading and event to `udp_listener.py` on dev10, gets an ack carrying the message's CRC-16, and the server stores it.

Two machines are involved:

- **dev10** (192.168.1.88, Ubuntu): runs the server, and has the ESP32 plugged into its USB.
- **The Arch VM** (VirtualBox guest on dev10): builds and flashes the firmware, through USB passthrough.

## 1. Server on dev10

1. Get the repo onto dev10. If logger-server isn't pushed yet, push it from the VM first (`git push -u origin main` in `~/dev/github/logger-server`). Then, on dev10:

   ```bash
   git clone https://github.com/xygnium/logger-server.git ~/dev/github/logger-server
   ```

   If it's already cloned, run `git pull` in it instead.

2. Start the server by hand for this test, storing to a test database:

   ```bash
   cd ~/dev/github/logger-server
   ./logserv.sh stop                      # if the service is running
   ./udp_listener.py --db /tmp/test.sqlite --verbose
   ```

   Expect `listening on UDP 8080`. Leave it running in its own terminal.

3. Check the firewall:

   ```bash
   sudo ufw status
   ```

   If it says `active`, allow the port with `sudo ufw allow 8080/udp`. If `inactive`, nothing to do.

4. Check the server from the VM, without the logger. On the VM:

   ```bash
   python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2); s.sendto(b'hello test', ('192.168.1.88', 8080)); print(s.recv(100))"
   ```

   Pass: it prints `b'ack 2026-...Z xxxx'`, and the dev10 terminal shows `hello test  [not stored: not a data or event message]`, which is expected here. A timeout means the server isn't running, the firewall blocks it, or the VM can't reach dev10. Fix that before going on.

## 2. Firmware on the VM

1. Attach the board to the VM. On dev10:

   ```bash
   ./vb-usb-attach.py esp32tty --vm Arch-03
   ```

   On the VM, `ls /dev/ttyUSB0` should show the port.

2. Build, flash and open the console:

   ```bash
   cd ~/dev/github/esp32-dev/ambient
   ./build.sh && ./flash.sh && ./monitor.sh
   ```

   Quit the monitor with Ctrl+].

## 3. Set the logger up for the test

Type these on the monitor console. Settings are saved in flash and survive a restart and a reflash; a new board starts with WiFi and the listener `not set`.

1. `config get`. If `wifi` doesn't show the right network, run `config wifi <ssid> <password>`.
2. If `listener` isn't `192.168.1.88:8080`, run `config listener 192.168.1.88 8080`.
3. `quiet off`: show each sent message on the console too.
4. `status`: expect `wifi connected to ...`, `listener 192.168.1.88:8080`, and the send counts.

## 4. What a pass looks like

Let it run for a few sample intervals.

- **dev10 terminal:** the boot and clock events, then 6 `data` lines per sample, one per value.
- **Logger console:** a `sent:` line for each, and no `expected ack failed`.
- **Logger `status`:** `sends ok` goes up; `no reply` and `send failed` stay at 0. The clock line's round trip is a few ms.
- **Database:** `sqlite3 /tmp/test.sqlite "select count(*) from readings"` matches the `data` lines.

## If it fails

| Symptom | Likely cause |
|---|---|
| `wifi not connected` or `not set` | Wrong or missing SSID or password: fix with `config wifi <ssid> <password>` |
| Logger counts `no reply`, nothing on dev10 | Wrong listener address (check `config get`), server not running, or the dev10 firewall |
| Lines on dev10, but logger counts `no reply` | The ack isn't getting back to the logger |
| `expected ack failed` | The CRC in the ack doesn't match the message: the server and firmware disagree on the CRC |
| `send failed` | WiFi dropped at send time; check `reconnects` and `rssi` |

These causes are guesses until a check confirms them.

## Afterwards

Stop the hand-started `udp_listener.py` (Ctrl+C) and start the service again: `./logserv.sh start`.
