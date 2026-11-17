# Bkool Trainer Classic – USB protocol

Reverse engineered from a Bkool Trainer Classic, firmware **V01.13**. Not an official Bkool document.
Other firmware versions may differ; reports welcome.

## Hardware

- The brake unit's USB cable is an **FTDI FT232R** USB-serial converter (VID `0403`, PID `6001`).
  The trainer is powered from USB.
- Main controller: Freescale HC08 (Bkool's own software flashes it over this port with
  `hc08sprg.exe ! 115200 "<file>"`).
- Serial settings: **115200 baud, 8N1**, no flow control. Lines end with `\r\n`.

## Start-up

After power-on the trainer homes its resistance magnets and prints:

```
MAGNETS TO HOME
PHOTO INT. FOUND AND INIT
FORCE MAGNETS TO POSITION 250
POSITIONING OK
MAGNETS TO HOME
CHANGING STATUS TO TX_CONSOLE
```

## Console output (about twice per second)

```
WIND:0.000000 i:0.000000 CR:0.008000 M:80 DRAFT:1.000000 PHOTOINT:0
CAD:0rpm FREQ:3260rpm SPD(r/v):30.7/ 0.0 Kmh POS:110.2 MOT:102 TEMP:315 TARGET:61.5w MAGNET:54.4w SHOW:137w
```

| Field | Meaning |
|---|---|
| `WIND` | wind speed, m/s |
| `i` | slope as a fraction (`0.05` = 5 %) |
| `CR` | rolling resistance coefficient |
| `M` | mass in kg (Bkool's software sends rider + bike) |
| `DRAFT` | drafting factor |
| `PHOTOINT` | magnet position sensor (photo interrupter) |
| `CAD` | cadence – always 0 on this hardware |
| `FREQ` | flywheel rpm |
| `SPD(r/v)` | real wheel speed / virtual speed, km/h |
| `POS`, `MOT` | magnet position / motor output |
| `TEMP` | temperature-like value (decreases while running) |
| `TARGET` | power the internal physics model wants, W |
| `MAGNET` | power applied by the brake, W |
| `SHOW` | power the trainer reports to the rider, W (used as "power") |

Without commands the trainer simulates a flat road with the defaults above.

## Commands

All commands are ASCII, framed `$` … `#`.

### Hello

`$PC#` → `$RL<12 hex id>V<version>#`, e.g. `$RL0004A3xxxxxxV01.13#`.
(Bkool's software sends `$PC#` to find the port, then `$RS#`, which resets the trainer.)

### Settings: `$C<letter><unsigned integer>#` → `$C<letter>OK#`

| Command | Sets | Value | Example |
|---|---|---|---|
| `CS` | slope (`i`) | slope % × 100; a leading `-` for downhill | `$CS500#` = 5 %, `$CS-300#` = −3 % |
| `CF` | rolling resistance (`CR`) | crr × 1000 | `$CF8#` = 0.008 (default), `$CF4#` = 0.004 |
| `CW` | mass (`M`) | kg (8-bit) | `$CW85#` |
| `CN` | wind (`WIND`) | km/h × 100 (shown in m/s) | `$CN1000#` = 10 km/h |
| `CD` | draft | accepted (`$CDOK#`), no visible effect | |

Notes:

- The value parser computes `value = value*10 + (c - '0')` for each character into a 16-bit value.
  **No decimals**: `0.5` turns into garbage. A leading `-` works for `CS`.
- The parser looks for `C` followed by a letter anywhere in the frame, so stray bytes before it are ignored.
- A power cycle (USB unplug) restores the defaults: slope 0, CR 0.008, M 80, wind 0.

## Private ANT profile (wireless)

Bkool's PC software ("Bkool Indoor") describes this model as "Bkool Trainer Classic" (legacy name
"BCycling") on a private ANT channel: device type 40, RF 2440 MHz (channel 40), period 8100,
with a non-ANT+ network key. Its wireless commands are 8-byte pages `[cmd, 0x11, 0x22, 0x33, value…]`
(3 weight, 4 slope, 5 draft, 6 wind, 7 rolling resistance). These are **not** accepted over USB.
Standard ANT+ apps cannot see this trainer.

## Newer Bkool trainers (Pro / Go generation)

These have an nRF51 module with ANT+ FE-C and BLE (FTMS, cycling power). Their firmware is updated
over BLE: write `F3 5A BE AA FA BA DA 00` to characteristic `f03ee002-4910-473c-be46-960948c2f59c`,
the unit reboots as `BCycling_DFU`, then Nordic legacy DFU (service 1530, no init packet, CRC16-CCITT,
16-byte packets). That firmware does not apply to the Classic.
