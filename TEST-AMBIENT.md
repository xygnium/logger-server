# Test: ambient logger to logger-server

Checks the push link only: the ambient logger sends its status line to `udp_listener.py` on dev10, and gets an ack back. Ambient has no sensor readings yet, and the server stores nothing yet.

Two machines are involved:

- **dev10** (192.168.1.88, Ubuntu): runs the server, and has the ESP32 plugged into its USB.
- **The Arch VM** (VirtualBox guest on dev10): builds and flashes the firmware, through USB passthrough.

## 1. Server on dev10

1. Get the repo onto dev10. If logger-server isn't pushed yet, push it from the VM first (`git push -u origin main` in `~/dev/github/logger-server`). Then, on dev10:

   ```bash
   git clone https://github.com/xygnium/logger-server.git ~/dev/github/logger-server
   ```

   If it's already cloned, run `git pull` in it instead.

2. Start the server by hand for this test:

   ```bash
   cd ~/dev/github/logger-server
   ./udp_listener.py
   ```

   Expect `listening on UDP 8080`. Leave it running in its own terminal. (Running it as a service is in the README; do that once the test passes.)

3. Check the firewall:

   ```bash
   sudo ufw status
   ```

   If it says `active`, allow the port with `sudo ufw allow 8080/udp`. If `inactive`, nothing to do.

4. Check the server from the VM, without the logger. On the VM:

   ```bash
   python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(2); s.sendto(b'hello test', ('192.168.1.88', 8080)); print(s.recv(100))"
   ```

   Pass: it prints `b'ack 2026-...Z'`, and the dev10 terminal shows a line ending in `hello test`. That line is marked `BAD`, since `hello test` isn't a full hello line; that's expected here. A timeout means the server isn't running, the firewall blocks it, or the VM can't reach dev10. Fix that before going on.

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

   This replaces whatever was on the board (`ads1115-probe` at present). Quit the monitor with Ctrl+].

## 3. Set the logger up for the test

Type these on the monitor console. WiFi and the listener come only from these commands; nothing in the build supplies them. Settings are saved in flash, survive a restart and a reflash, and a new board starts with WiFi and the listener `not set`.

1. `config get`. If `wifi` doesn't show the right network, or shows `not set`, run `config wifi <ssid> <password>`.
2. If `listener` isn't `192.168.1.88:8080`, run `config listener 192.168.1.88 8080`.
3. `config interval 2m 2m`: sample and push every 2 minutes instead of pushing hourly.
4. `quiet off`: show successful pushes on the console too.
5. `push`: push now.
6. `status`: expect `wifi connected to ...`, `listener 192.168.1.88:8080`, and the push counts.

## 4. What a pass looks like

Let it run for 30 minutes, about 15 pushes.

- **dev10 terminal:** one line per push, from the logger's IP, like

  ```
  GOOD 05:41:02 192.168.1.x:xxxxx hello seq=3 up=362 rssi=-58 ap=... ip=... mac=... reconnects=0 push_s=120 vin_mv=...
  ```

  `seq` goes up by one each time, the lines are about 120 s apart, and each starts with `GOOD`. The first line after a logger restart is `OK`. `OK` from weak rssi or a reconnect, or `BAD` from a `seq` gap, needs noting.
- **Logger `status`:** `pushes ok` matches the number of lines on dev10; `no reply` and `send failed` stay at 0.

## If it fails

| Symptom | Likely cause |
|---|---|
| `wifi not connected` or `not set` | Wrong or missing SSID or password: fix with `config wifi <ssid> <password>` |
| Logger counts `no reply`, nothing on dev10 | Wrong listener address (check `config get`), server not running, or the dev10 firewall |
| Lines on dev10, but logger counts `no reply` | The ack isn't getting back to the logger. Note how often, and report it |
| `send failed` | WiFi dropped at push time; check `reconnects` and `rssi` |

These causes are guesses until a check confirms them.

## Afterwards

- To return to hourly pushes: `config interval 2m 1h`.
- To keep the server running without a terminal, install the service (README, "As a service on dev10"). Stop the hand-started `udp_listener.py` first.
