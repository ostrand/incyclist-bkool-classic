# Driver

Incyclist talks to trainers through [incyclist/devices](https://github.com/incyclist/devices). Serial
trainers (Daum, Kettler) are adapters registered with a protocol name; the list in Incyclist's
USB/serial settings comes straight from that registry. This driver adds one more: **Bkool Classic**.

| File | |
|---|---|
| `adapter.ts` | the adapter (`src/serial/bkool/classic/adapter.ts` in incyclist/devices) |
| `adapter.unit.test.ts` | Vitest unit tests against a mocked serial port |
| `0001-bkool-classic-adapter.patch` | everything as one `git am` patch: adapter, tests, registration in `src/serial/index.ts`, and an optional `baudRate` for `SerialInterface.openPort()` |
| `build-ui.sh` | rebuilds the pre-built Incyclist interface in `../incyclist/incyclist-bkool-ui` |

## Behaviour

- `check()` (used when Incyclist scans a COM port): opens 115200 8N1, sends `$PC#`, and succeeds on a
  `$RL…#` reply or on console telemetry.
- `start()`: sends `$CW<rider+bike kg>#`, `$CN0#`, `$CF4#` (rolling resistance 0.004), `$CS0#`, then
  emits data every second.
- Smart Trainer mode (default): each slope request becomes `$CS<slope % × 100>#`, clamped to ±25 % and
  only sent when it changes. Power-meter mode is also offered.
- Data: power = console `SHOW`, speed = real wheel speed `SPD`. Incyclist's mode computes the virtual speed.

## Rebuilding the interface

Needs git, Node.js 22+ and bash (Linux, macOS, or Git Bash/WSL on Windows):

```
bash build-ui.sh                        # Incyclist 26.10.1 → web-ui v26.10.10 + devices v3.0.42
bash build-ui.sh v26.11.9 v3.0.46       # other versions: web-ui tag + devices tag from its package-lock.json
```

To find the web-ui version inside your Incyclist, search its bundled `index-*.js` for `"26.` or check
the version Incyclist reports. The build is reproducible: an unpatched build is identical to the official
bundle except for the recorded build path.

## Tests

In a checkout of incyclist/devices with the patch applied:

```
npm ci --ignore-scripts
npx vitest run src/serial/bkool
```
