#!/usr/bin/env python
import subprocess
import os
import json
from pathlib import Path
import datetime

EXAMPLE_OF_WAYBAR_WIDGET = """
    "custom/niri-mode": {
        "format": " {} ",
        "exec": "cat $XDG_RUNTIME_DIR/.niri_active_bind_group",
        "return-type": "json",
        "signal": 9
    },
"""


KEYBINDING_CHANGE = "Keybinding group changed: "
WAYBAR_SIGNAL = 9
STATE_PATH = os.environ.get("XDG_RUNTIME_DIR") or Path("~/.local/state/").expanduser()
assert Path(STATE_PATH).exists(), "Setup $XDG_RUNTIME_DIR or ~/.local/state"
STATE_PATH = Path(STATE_PATH).joinpath(".niri_active_bind_group")


def on_niri_keybinding_change(event: str):
    event = event.rstrip()
    # TODO: unescape quotes etc
    name = (
        "normal" if event == "None" else event.removeprefix('Some("').removesuffix('")')
    )

    data = {
        "text": name,
        "tooltip": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    Path(STATE_PATH).write_text(json.dumps(data))
    os.system(f"kill -SIGRTMIN+{WAYBAR_SIGNAL} $(pidof waybar)")


def on_niri_event(event: str):
    if event.startswith(KEYBINDING_CHANGE):
        return on_niri_keybinding_change(event[len(KEYBINDING_CHANGE) :])


def query_niri():
    niri_path = os.environ.get("NIRI_PATH") or "niri"
    """ Run a a niri msg event process"""
    process = subprocess.Popen(
        [niri_path, "msg", "event-stream"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,  # bufsize=1 enables line_buffering
        text=True,
    )

    assert process.stdout is not None
    while True:
        line = process.stdout.readline()
        if line is None:
            break
        on_niri_event(line)


def already_exists():
    """Very rough check if we are already running"""
    ps = subprocess.Popen(
        ["ps", "aux"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
    )
    assert ps.stdout is not None
    ps.wait()
    lines = ps.stdout.readlines()
    lines = [line for line in lines if "/niri-mode.py" in line and "python" in line]
    return lines != []


if already_exists():
    print("NIRI-MODE IS ALREADY RUNNING")
    exit()

query_niri()
