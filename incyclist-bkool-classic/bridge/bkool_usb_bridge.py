"""
bkool_usb_bridge.py - make a USB-connected Bkool Trainer Classic show up in Incyclist.

How it works
  Trainer --USB serial (COM, 115200)--> this bridge --Wahoo "Direct Connect" (FTMS over TCP)--> Incyclist
  The bridge reads speed/power from the trainer's USB console and presents itself on the
  local network as a standard FTMS smart trainer called "Bkool USB Bridge".

Status
  * Speed + power from the trainer -> Incyclist.
  * Incyclist slope + rolling resistance -> trainer, using the trainer's USB text commands:
      $CS<n>#  slope      (n = slope % x 100, e.g. $CS500# = 5 %)
      $CF<n>#  rolling resistance (n = crr x 1000, default 8)
      $CW<n>#  rider weight kg
      $CN<n>#  wind (km/h x 100)
    Negative slopes are sent as 0 % unless --negative-slopes is given (encoding still unconfirmed).
  * ERG / target-power mode is not supported by the trainer; it is logged and ignored.

Setup (once)
  py -m pip install pyserial zeroconf
Run
  py bkool_usb_bridge.py                 (auto-detects the FTDI COM port)
  py bkool_usb_bridge.py COM3 --fake-cadence 85 --weight 85
Then in Incyclist: Settings > Devices, make sure "Direct Connect / WiFi" is enabled, search, pick
"Bkool USB Bridge" as the controllable trainer. Allow Python through the Windows firewall if asked.
Log: bkool_usb_bridge_log.txt
"""
import argparse
import re
import socket
import struct
import threading
import time

import serial
from serial.tools import list_ports

try:
    from zeroconf import ServiceInfo, Zeroconf
except ImportError:
    Zeroconf = None

PORT = 36866
NAME = "Bkool USB Bridge"
LOG = open("bkool_usb_bridge_log.txt", "a", encoding="utf-8")


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()


def u128(short):
    return bytes.fromhex(f"0000{short:04x}00001000800000805f9b34fb")


FTMS = u128(0x1826)
C_FEATURE, C_BIKE_DATA, C_RES_RANGE, C_PWR_RANGE, C_CP, C_STATUS = (
    u128(0x2ACC), u128(0x2AD2), u128(0x2AD6), u128(0x2AD8), u128(0x2AD9), u128(0x2ADA))
READ, WRITE, NOTIFY = 1, 2, 4
CHARS = [
    (C_FEATURE, READ),
    (C_BIKE_DATA, NOTIFY),
    (C_RES_RANGE, READ),
    (C_PWR_RANGE, READ),
    (C_CP, WRITE | NOTIFY),
    (C_STATUS, NOTIFY),
]
STATIC = {
    # features: cadence(1) + power measurement(14); targets: resistance(2) + power(3) + sim(13)
    C_FEATURE: struct.pack("<II", (1 << 1) | (1 << 14), (1 << 2) | (1 << 3) | (1 << 13)),
    C_RES_RANGE: struct.pack("<hhH", 0, 1000, 10),
    C_PWR_RANGE: struct.pack("<hhH", 0, 1500, 1),
}

# ---------------------------------------------------------------- trainer side (USB serial)
state = {"speed": 0.0, "power": 0, "cadence": 0, "last": 0.0}
trainer = {"ser": None, "lock": threading.Lock(), "weight": 80, "neg": False, "last_slope": None}
RX = re.compile(r"CAD:\s*(\d+)rpm.*SPD\(r/v\):\s*([-\d.]+)/\s*([-\d.]+).*SHOW:\s*(-?\d+)w")


def serial_reader(port):
    while True:
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            log(f"trainer: opened {port}")
            trainer["ser"] = ser
            trainer["last_slope"] = None
            trainer["last_crr"] = None
            for c in (f"$CW{trainer['weight']}#", "$CF8#", "$CN0#", "$CS0#"):
                send_cmd(c)
            buf = b""
            while True:
                buf += ser.read(ser.in_waiting or 1)
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    m = RX.search(raw.decode("ascii", "replace"))
                    if m:
                        state["cadence"] = int(m.group(1))
                        state["speed"] = max(0.0, float(m.group(2)))
                        state["power"] = max(0, int(m.group(4)))
                        state["last"] = time.time()
                    elif b"OK#" in raw:
                        log(f"trainer: {raw.strip().decode('ascii', 'replace')}")
        except Exception as e:
            trainer["ser"] = None
            log(f"trainer: serial error {e!r}, retrying in 2 s")
            time.sleep(2)


def send_cmd(cmd):
    ser = trainer["ser"]
    if ser is None:
        log(f"trainer not connected, dropped {cmd}")
        return
    with trainer["lock"]:
        ser.write(cmd.encode("ascii"))


def apply_to_trainer(kind, value):
    if kind == "slope %":
        v = max(-2500, min(int(round(value * 100)), 2500))   # cap at +/-25 %
        if v < 0:
            v = (v & 0xFFFF) if trainer["neg"] else 0
        if v != trainer["last_slope"]:
            trainer["last_slope"] = v
            send_cmd(f"$CS{v}#")
            log(f"slope {value:+.2f} %  -> $CS{v}#")
    elif kind == "crr":
        v = max(1, min(int(round(value * 1000)), 50))
        if v != trainer.get("last_crr"):
            trainer["last_crr"] = v
            send_cmd(f"$CF{v}#")
            log(f"rolling resistance {value:.4f} -> $CF{v}#")
    else:
        log(f"Incyclist asked for {kind} = {value} (not supported by this trainer, ignored)")


# ---------------------------------------------------------------- Direct Connect (DirCon) server
def frame(msg_id, seq, rc, body=b""):
    return struct.pack(">BBBBH", 1, msg_id, seq, rc, len(body)) + body


class Client:
    def __init__(self, sock, addr, fake_cadence):
        self.sock, self.addr, self.fake_cadence = sock, addr, fake_cadence
        self.subs = set()
        self.lock = threading.Lock()
        self.alive = True

    def send(self, data):
        with self.lock:
            self.sock.sendall(data)

    def notify(self, char, payload):
        if char in self.subs:
            self.send(frame(6, 0, 0, char + payload))

    def handle(self, msg_id, seq, body):
        if msg_id == 1:                                   # discover services
            return frame(1, seq, 0, FTMS)
        if msg_id == 2:                                   # discover characteristics
            if body[:16] != FTMS:
                return frame(2, seq, 3, body[:16])
            return frame(2, seq, 0, FTMS + b"".join(u + bytes([p]) for u, p in CHARS))
        if msg_id == 3:                                   # read
            c = body[:16]
            if c not in STATIC:
                return frame(3, seq, 5, c)
            return frame(3, seq, 0, c + STATIC[c])
        if msg_id == 4:                                   # write
            c, data = body[:16], body[16:]
            if c != C_CP:
                return frame(4, seq, 5, c)
            self.send(frame(4, seq, 0, c))
            self.control_point(data)
            return None
        if msg_id == 5:                                   # enable/disable notifications
            c, en = body[:16], body[16] if len(body) > 16 else 1
            (self.subs.add if en else self.subs.discard)(c)
            log(f"incyclist: notifications {'on' if en else 'off'} for {c[2:4].hex()}")
            return frame(5, seq, 0, c)
        return frame(msg_id, seq, 1)

    def control_point(self, d):
        op = d[0] if d else 0xFF
        if op == 0x11 and len(d) >= 7:
            wind, grade, crr, cw = struct.unpack("<hhBB", d[1:7])
            apply_to_trainer("slope %", grade / 100.0)
            if crr:
                apply_to_trainer("crr", crr * 0.0001)
        elif op == 0x05 and len(d) >= 3:
            apply_to_trainer("target power W", struct.unpack("<h", d[1:3])[0])
        elif op == 0x04 and len(d) >= 2:
            apply_to_trainer("resistance", d[1])
        else:
            log(f"incyclist: control op 0x{op:02x} {d.hex()}")
        self.notify(C_CP, bytes([0x80, op, 0x01]))

    def pump(self):
        while self.alive:
            time.sleep(0.25)
            fresh = time.time() - state["last"] < 3
            spd = state["speed"] if fresh else 0.0
            pwr = state["power"] if fresh else 0
            cad = state["cadence"] or (self.fake_cadence if spd > 3 else 0)
            # flags: cadence present (bit2) + power present (bit6); speed always present
            payload = struct.pack("<HHHh", 0x0044, int(spd * 100), int(cad * 2), int(pwr))
            try:
                self.notify(C_BIKE_DATA, payload)
            except OSError:
                self.alive = False

    def run(self):
        threading.Thread(target=self.pump, daemon=True).start()
        buf = b""
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= 6:
                    ver, msg_id, seq, rc, ln = struct.unpack(">BBBBH", buf[:6])
                    if len(buf) < 6 + ln:
                        break
                    body, buf = buf[6:6 + ln], buf[6 + ln:]
                    resp = self.handle(msg_id, seq, body)
                    if resp:
                        self.send(resp)
        except OSError:
            pass
        self.alive = False
        log(f"incyclist disconnected {self.addr}")


def tcp_server(fake_cadence):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(4)
    log(f"Direct Connect server listening on TCP {PORT}")
    while True:
        s, a = srv.accept()
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        log(f"incyclist connected from {a}")
        threading.Thread(target=Client(s, a, fake_cadence).run, daemon=True).start()


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def advertise():
    txt = {"ble-service-uuids": "0x1826", "mac-address": "B0-0B-B0-0B-00-01", "serial-number": "BKUSB0001"}
    if Zeroconf is None:
        log("zeroconf not installed (py -m pip install zeroconf). Fallback with Bonjour:")
        log(f'  dns-sd -R "{NAME}" _wahoo-fitness-tnp._tcp local {PORT} ble-service-uuids=0x1826 serial-number=BKUSB0001')
        return None
    ip = local_ip()
    info = ServiceInfo("_wahoo-fitness-tnp._tcp.local.", f"{NAME}._wahoo-fitness-tnp._tcp.local.",
                       addresses=[socket.inet_aton(ip)], port=PORT, properties=txt,
                       server=f"{socket.gethostname()}.local.")
    zc = Zeroconf()
    zc.register_service(info)
    log(f"advertising '{NAME}' via mDNS on {ip}:{PORT}")
    return zc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", nargs="?")
    ap.add_argument("--fake-cadence", type=int, default=0,
                    help="cadence to report while moving (trainer has no cadence sensor)")
    ap.add_argument("--weight", type=int, default=80, help="rider weight in kg sent to the trainer")
    ap.add_argument("--negative-slopes", action="store_true",
                    help="send negative slopes as 16-bit two's complement (experimental)")
    a = ap.parse_args()
    trainer["weight"] = max(30, min(a.weight, 150))
    trainer["neg"] = a.negative_slopes
    port = a.port or next((p.device for p in list_ports.comports() if p.vid == 0x0403), None)
    if not port:
        raise SystemExit("No FTDI COM port found - is the trainer's USB cable connected?")
    threading.Thread(target=serial_reader, args=(port,), daemon=True).start()
    threading.Thread(target=tcp_server, args=(a.fake_cadence,), daemon=True).start()
    zc = advertise()
    try:
        while True:
            time.sleep(5)
            age = time.time() - state["last"]
            log(f"trainer: {state['speed']:.1f} km/h  {state['power']} W  "
                f"({'live' if age < 3 else 'no data'})")
    except KeyboardInterrupt:
        pass
    finally:
        if zc:
            zc.unregister_all_services()
            zc.close()


if __name__ == "__main__":
    main()
