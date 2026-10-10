"""Drive the Mi Bedside Lamp 2 from Witcher 3's equipped sign.

modLampSync writes the equipped sign into
Documents/The Witcher 3/dx12user.settings under [LampSync] Sign.
That value is the game enum, not the hotkey order:

    0 Aard, 1 Yrden, 2 Igni, 3 Quen, 4 Axii, 5 None
"""

import json
import re
import sys
import time
from pathlib import Path

from miio import Yeelight

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "lamp_config.json"
LOG_PATH = ROOT / "lamp_sync.log"
SETTINGS_CANDIDATES = (
    Path.home() / "Documents" / "The Witcher 3" / "dx12user.settings",
    Path.home() / "Documents" / "The Witcher 3" / "user.settings",
)

# Game enum ESignType. Yrden is 1 and Igni is 2.
SIGNS = {
    0: {"name": "Aard", "rgb": (0, 90, 255)},
    1: {"name": "Yrden", "rgb": (180, 50, 255)},
    2: {"name": "Igni", "rgb": (255, 33, 0), "brightness": 80},
    3: {"name": "Quen", "rgb": (255, 100, 30)},
    4: {"name": "Axii", "rgb": (50, 255, 20)},
    5: {"name": "None", "rgb": (80, 80, 80)},
}

FADE_MS = 900
KEEPALIVE_S = 20

SECTION_RE = re.compile(r"(?m)^\[LampSync\][^\S\r\n]*\r?\n(.*?)(?=^\[|\Z)", re.S)
SIGN_RE = re.compile(r"(?m)^Sign=([0-9]+(?:\.[0-9]+)?)")


def log(message):
    if sys.stdout is not None:
        try:
            print(message, flush=True)
        except OSError:
            pass
    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    except OSError:
        pass


def load_config():
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    ip = data["lamp_ip"]
    token = data["lamp_token"]
    if not ip or not token:
        raise SystemExit(f"Missing lamp_ip or lamp_token in {CONFIG_PATH}")
    return ip, token


def read_text(path: Path):
    last_error = None
    for _ in range(6):
        try:
            data = path.read_bytes()
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
            continue
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            return data.decode("utf-16")
        if data.startswith(b"\xef\xbb\xbf"):
            return data.decode("utf-8-sig")
        return data.decode("utf-8", errors="replace")
    raise last_error


def parse_sign(text: str):
    """Return the equipped sign id, or None if the mod has not written one yet."""
    section = SECTION_RE.search(text)
    if not section:
        return None
    match = SIGN_RE.search(section.group(1))
    if not match:
        return None
    sign_id = int(float(match.group(1)))
    if sign_id not in SIGNS:
        return None
    return sign_id


def settings_path():
    for path in SETTINGS_CANDIDATES:
        if path.exists():
            return path
    return SETTINGS_CANDIDATES[0]


class Lamp:
    def __init__(self, ip, token):
        log(f"Connecting to lamp at {ip}...")
        self.device = Yeelight(ip, token, model="yeelink.light.bslamp2")
        status = self.device.status()
        log(f"Lamp connected. Power is {'on' if status.is_on else 'off'}.")
        self.ready = False
        self.brightness = None
        self.current = None
        self.next_keepalive = time.monotonic() + KEEPALIVE_S

    def ensure_fresh(self):
        """Handshake before the lamp forgets the last clock time."""
        now = time.monotonic()
        if now < self.next_keepalive:
            return
        try:
            self.device.send_handshake()
        except Exception as exc:
            self.next_keepalive = now + 5
            log(f"Lamp keepalive failed: {exc}")
            return
        self.next_keepalive = time.monotonic() + KEEPALIVE_S

    def show(self, sign_id):
        if sign_id == self.current:
            return
        self.ensure_fresh()
        color = SIGNS[sign_id]
        red, green, blue = color["rgb"]
        brightness = color.get("brightness", 100)
        if not self.ready:
            status = self.device.status()
            if not status.is_on:
                self.device.on()
            self.ready = True
        if brightness != self.brightness:
            self.device.set_brightness(brightness, transition=FADE_MS)
            self.brightness = brightness
        rgb = (red << 16) | (green << 8) | blue
        self.device.send("set_rgb", [rgb, "smooth", FADE_MS])
        self.current = sign_id
        self.next_keepalive = time.monotonic() + KEEPALIVE_S
        log(f"Sign: {color['name']}  rgb({red}, {green}, {blue})  brightness {brightness}  fade {FADE_MS}ms")


def main():
    ip, token = load_config()
    lamp = Lamp(ip, token)
    path = settings_path()
    log(f"Watching {path}")
    log("Load a save. The mod writes [LampSync] on spawn and on every sign change.")
    log("Ctrl+C stops the sync.")

    announced_wait = False
    while True:
        try:
            if not path.exists():
                if not announced_wait:
                    log("Settings file is not there yet.")
                    announced_wait = True
                time.sleep(0.5)
                continue

            lamp.ensure_fresh()
            sign_id = parse_sign(read_text(path))
            if sign_id is None:
                if not announced_wait and lamp.current is None:
                    log("Waiting for [LampSync]. Load a save so the mod can write the equipped sign.")
                    announced_wait = True
            else:
                announced_wait = False
                lamp.show(sign_id)
        except KeyboardInterrupt:
            log("Stopped.")
            return
        except Exception as exc:
            log(f"Lamp or settings error: {exc}")
            lamp.current = None
        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
