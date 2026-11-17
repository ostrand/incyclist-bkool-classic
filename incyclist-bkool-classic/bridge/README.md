# Bkool Classic → Direct Connect bridge

`bkool_usb_bridge.py` reads a Bkool Trainer Classic over its USB cable and presents it on the local
network as a standard **FTMS smart trainer** via **Wahoo Direct Connect** (mDNS `_wahoo-fitness-tnp._tcp`,
TCP port 36866). It needs no modified app; any app with Direct Connect support can connect to it.
It has been tested with a simulated client, not yet end to end with every app.

```
py -m pip install -r requirements.txt
py bkool_usb_bridge.py --fake-cadence 85 --weight 85
py bkool_usb_bridge.py COM3 --negative-slopes      # explicit port, allow downhill
```

Then enable Direct Connect / WiFi in the app and choose **Bkool USB Bridge**. Allow Python through the
Windows firewall when asked.

- Speed and power from the trainer → app (FTMS Indoor Bike Data).
- App slope and rolling resistance → trainer (`$CS…#`, `$CF…#`).
- Negative slopes are sent as 0 % unless `--negative-slopes` is given. The trainer accepts `$CS-300#`;
  without the flag the bridge stays conservative.
- `--weight` (kg) is sent to the trainer at start; use rider + bike mass.
- ERG/target power is not supported by the trainer and is ignored.
- Don't run it together with the Incyclist driver: both need the COM port.

Log: `bkool_usb_bridge_log.txt` in the current folder.
