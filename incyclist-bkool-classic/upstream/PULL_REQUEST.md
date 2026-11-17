# Pull request for incyclist/devices

## Title

feat(serial): add Bkool Classic (USB) trainer adapter

## Description

This adds support for the **Bkool Trainer Classic** connected via its USB cable.

The Classic predates ANT+ FE-C/BLE: its wireless link uses a private Bkool ANT profile, so it can't be
used with Incyclist today. Its USB cable, however, is an FTDI serial port (115200 8N1) on which the
firmware streams a text console and accepts simple text commands. That makes it a good fit for the
existing serial adapter framework, alongside Daum and Kettler.

**Changes**

- `src/serial/bkool/classic/adapter.ts`: new adapter, registered as serial protocol `Bkool Classic`.
  - `check()`: sends `$PC#`; succeeds on the `$RL<id>V<version>#` reply or on console telemetry.
  - `start()`: sends total mass (`$CW<kg>#`), wind 0 (`$CN0#`), rolling resistance 0.004 (`$CF4#`), slope 0 (`$CS0#`).
  - Smart Trainer mode (default) sends the slope as `$CS<slope*100>#` (negative supported, clamped ±25 %,
    de-duplicated); Power Meter mode is also available.
  - Emits power (console `SHOW`) and wheel speed (`SPD`). The hardware has no cadence sensor.
- `src/serial/index.ts`: registration and export.
- `src/serial/base/serial-interface.ts`: `openPort(path, portProps?)` accepts optional port properties
  so an adapter can open at a different baud rate (backwards compatible).
- `src/serial/bkool/classic/adapter.unit.test.ts`: 8 tests with `MockBinding` (registration, detection,
  start sequence, slope encoding/clamping/de-duplication, data emission, parsing).

**Testing**

- `npx vitest run src/serial`: all new tests pass. The only failure, `serial-interface.test.ts > connect
  attempt with CppBindig`, fails the same way on `main` without this change (native binding not built in
  my environment).
- Ridden on a real trainer (firmware V01.13) with Incyclist 26.10.1, with the adapter built into web-ui
  v26.10.10: detection, slope changes up/down, power/speed display.

**Protocol notes**

Reverse engineered; documented in <https://github.com/OWNER/incyclist-bkool-classic/blob/main/docs/protocol.md>.
Commands are `$C<letter><unsigned int>#` → `$C<letter>OK#`: `CS` slope % × 100, `CF` crr × 1000,
`CW` mass kg, `CN` wind km/h × 100. Integers only.

**Open points**

- Power accuracy of the trainer's own estimate is unverified against a power meter.
- Only one firmware version tested.

## How to submit

1. Fork <https://github.com/incyclist/devices> on GitHub.
2. In a terminal (Git Bash / PowerShell):
   ```
   git clone https://github.com/<your-user>/devices.git
   cd devices
   git checkout -b bkool-classic
   git am --3way path\to\incyclist-bkool-classic\driver\0001-bkool-classic-adapter.patch
   git commit --amend --reset-author --no-edit
   git push -u origin bkool-classic
   ```
   (`--reset-author` puts your own git name/e-mail on the commit.)
3. Open the pull request from the `bkool-classic` branch on GitHub, and paste the title and description
   above. Replace `OWNER` with your GitHub user name.
