#!/usr/bin/env python3
"""Compare the BMP388 pressure with the latest KRDU METAR.

Takes the BMP388 reading nearest the METAR time, converts it to sea level
(QNH) at the sensor's elevation, and prints it next to KRDU's altimeter
setting. Run on the logserv host. Database: $LOGSERV_DB or ~/logserv.sqlite.
"""
import json, os, re, sqlite3, urllib.request
from datetime import datetime, timezone

ELEV_M = 92.56  # ground 289.1 ft + 175 in to the sensor
URL = "https://aviationweather.gov/api/data/metar?ids=KRDU&format=json"
DB = os.environ.get("LOGSERV_DB", os.path.expanduser("~/logserv.sqlite"))

metar = json.load(urllib.request.urlopen(URL))[0]
obs = datetime.fromtimestamp(metar["obsTime"], timezone.utc)
krdu = int(re.search(r" A(\d{4})", metar["rawOb"]).group(1)) / 100 * 33.8639

db = sqlite3.connect(DB)
row = db.execute(
    "select timestamp, value from readings"
    " where sensor = 'bmp388' and data_type = 'pressure_pa' and status = 'ok'"
    " order by abs(julianday(timestamp) - julianday(?)) limit 1",
    (obs.strftime("%Y-%m-%dT%H:%M:%SZ"),)).fetchone()
if row is None:
    raise SystemExit("no BMP388 pressure readings in " + DB)
ts, pa = row
p = pa / 100
# NWS altimeter setting formula, the one behind the METAR A group.
n = 0.190284
qnh = ((p - 0.3) ** n + 1013.25 ** n * 0.0065 / 288.15 * ELEV_M) ** (1 / n)

print(metar["rawOb"])
print(f"KRDU   {obs:%Y-%m-%dT%H:%MZ}  QNH {krdu:8.2f} hPa")
print(f"BMP388 {ts}  station {p:8.2f} hPa  QNH {qnh:8.2f} hPa")
print(f"BMP388 - KRDU {qnh - krdu:+.2f} hPa")
