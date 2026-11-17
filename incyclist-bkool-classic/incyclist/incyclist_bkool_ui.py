"""
incyclist_bkool_ui.py - switch Incyclist between its normal interface and the Bkool Classic build.

The Bkool build (folder "incyclist-bkool-ui" next to this script) is Incyclist web-ui 26.10.10
with one addition: a "Bkool Classic" serial (USB) trainer driver.

It is activated with the "pageUrl" setting in %APPDATA%\\Incyclist\\settings.json. While pageUrl
is set, Incyclist loads that page and SKIPS its own interface auto-update (which would otherwise
replace "pageDir" and delete the previous interface folder). Nothing in the Incyclist program
folder is changed. "off" removes pageUrl, so Incyclist goes back to normal and updates again.

  py incyclist_bkool_ui.py on
  py incyclist_bkool_ui.py off
  py incyclist_bkool_ui.py status

Close Incyclist before switching. A backup settings.json.bkool-backup is written first.
"""
import json
import os
import pathlib
import shutil
import sys

SETTINGS = os.path.join(os.environ.get("APPDATA", ""), "Incyclist", "settings.json")
UI_DIR = pathlib.Path(__file__).resolve().parent / "incyclist-bkool-ui"


def load():
    if not os.path.exists(SETTINGS):
        sys.exit(f"{SETTINGS} not found - start Incyclist once first, then close it.")
    with open(SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    shutil.copy2(SETTINGS, SETTINGS + ".bkool-backup")
    tmp = SETTINGS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, SETTINGS)


cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
data = load()
if cmd == "on":
    index = UI_DIR / "index.html"
    if not index.exists():
        sys.exit(f"{index} not found")
    data["pageUrl"] = index.as_uri() + "#ride"
    # an older version of this script set pageDir to our folder; never let the updater own it
    if str(data.get("pageDir", "")).lower().startswith(str(UI_DIR).lower()):
        data.pop("pageDir", None)
    save(data)
    print(f"Incyclist will load the Bkool build: {data['pageUrl']}")
    print("(Incyclist's own interface updates are paused while this is on.)")
elif cmd == "off":
    data.pop("pageUrl", None)
    if str(data.get("pageDir", "")).lower().startswith(str(UI_DIR).lower()):
        data.pop("pageDir", None)
    save(data)
    print("Incyclist will load its normal interface (and update it again).")
else:
    print(f"settings: {SETTINGS}")
    print(f"pageUrl : {data.get('pageUrl', '(not set)')}")
    print(f"pageDir : {data.get('pageDir', '(not set)')}")
    print("Bkool build active" if "incyclist-bkool-ui" in str(data.get("pageUrl", "")) else "normal interface")
