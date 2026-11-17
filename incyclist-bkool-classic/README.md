# incyclist-bkool-classic

Ride an old **Bkool Trainer Classic** with [Incyclist](https://incyclist.com) over its **USB cable**:
power and speed go to Incyclist, and Incyclist sets the route's slope on the trainer.

The Classic predates ANT+ FE-C and Bluetooth smart trainers. Its wireless link is a private Bkool
ANT profile that only Bkool's own (discontinued) software understands, so current apps can't see it.
Its USB port, however, is a serial interface the trainer firmware still answers on. This project
documents that interface and adds a "Bkool Classic" driver to Incyclist.

> Not affiliated with Bkool or Incyclist. The protocol was reverse engineered from one trainer
> (firmware V01.13). Use at your own risk.

## What's in here

| Folder | What |
|---|---|
| [`incyclist/`](incyclist) | Pre-built Incyclist interface with the **Bkool Classic** driver, and a script to switch it on/off |
| [`driver/`](driver) | Driver source, unit tests, the patch for [incyclist/devices](https://github.com/incyclist/devices), and a build script |
| [`bridge/`](bridge) | Alternative: a Python bridge that presents the trainer as a standard smart trainer over **Wahoo Direct Connect** |
| [`docs/`](docs) | The USB protocol, and other things learned about old Bkool trainers |
| [`upstream/`](upstream) | Pull request text for getting the driver into official Incyclist |

## Requirements

- Bkool Trainer Classic with its USB cable plugged into the PC. It appears as an FTDI "USB Serial Port (COMx)";
  Windows installs the FTDI driver automatically.
- Windows with **Incyclist 26.10.x** (the pre-built interface is web-ui 26.10.10). For other versions, rebuild it, see [`driver/`](driver).
- Python 3 for the switch script (`py` on Windows).

## Install (Incyclist driver)

1. Install Incyclist, start it once, then close it.
2. Download this repository (Code → Download ZIP) and unpack it anywhere permanent.
3. In the `incyclist` folder run:
   ```
   py incyclist_bkool_ui.py on
   ```
4. Start Incyclist → **Settings → Devices** → open the **USB/serial** interface → protocol **Bkool Classic** → scan →
   select the trainer as controllable device (and as power/speed source).

`py incyclist_bkool_ui.py off` goes back to the normal Incyclist interface; `status` shows which one is active.

### How it works

Incyclist can load its interface from a page given by the `pageUrl` entry in
`%APPDATA%\Incyclist\settings.json`. The script points that at `incyclist/incyclist-bkool-ui`.
Nothing in the Incyclist program folder is modified (Incyclist verifies its own files).
While `pageUrl` is set, Incyclist **skips its own interface updates**. The `pageDir` entry is *not*
usable for this: Incyclist's updater overwrites it and deletes the folder it pointed to.

If Incyclist itself updates to a new version (e.g. 26.11), switch `off` and rebuild for that version.

## What works / limitations

- ✅ Detection on the serial port (`$PC#` hello), slope control in **Smart Trainer** mode (−25 … +25 %),
  rider+bike mass and rolling resistance sent at start.
- ✅ Power and wheel speed from the trainer. Incyclist computes the virtual speed from power and slope.
- ⚠️ **Power accuracy is unverified.** One comparison against heart rate suggested the trainer reads
  ~20–25 % low. If you have a power meter, pair it in Incyclist as the power source and keep the Bkool as
  the controllable trainer. Comparisons against a power meter are very welcome (open an issue).
- ❌ No cadence (the trainer has no cadence sensor). Use a cadence sensor or power meter.
- ❌ No ERG/target-power mode (the trainer has no such command).
- Descents: the brake can only remove resistance, not push. Incyclist's "Bike Reality Factor downhill"
  (default 50 %) scales negative slopes; uphill realism can be reduced with "Bike Reality Factor".
- Only one program can use the COM port at a time (don't run the bridge and Incyclist driver together).

## Alternative: Python Direct Connect bridge

[`bridge/`](bridge) needs no change to Incyclist: it reads the trainer over USB and advertises it on
the local network as an FTMS smart trainer via Wahoo Direct Connect, which Incyclist (and other apps
supporting Direct Connect) can connect to. See [bridge/README.md](bridge/README.md).

## Protocol

See [docs/protocol.md](docs/protocol.md). In short: 115200 8N1, the trainer streams a text console,
and accepts `$C<letter><integer>#` commands, e.g. `$CS500#` = 5 % slope.

## License

MIT, see [LICENSE](LICENSE). The pre-built interface in `incyclist/incyclist-bkool-ui` is built from
Incyclist's MIT-licensed web-ui and devices projects; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
"Bkool" and "Incyclist" are names of their respective owners and are used here only to describe compatibility.
