#!/usr/bin/env python

import sys
import os
import time
import subprocess
from typing import Optional

niri_bin = os.getenv("NIRI_BIN") or "niri"


class Niri:
    def __init__(self, niri_path) -> None:
        self.niri_path = niri_path

    def run(self, args: list[str], stdin: Optional[str] = None):
        p = subprocess.run(args, timeout=1, capture_output=True, text=True, input=stdin)
        if p.returncode != 0 or p.stderr:
            raise subprocess.SubprocessError(
                f"Niri failed: return-code: {p.returncode}, stderr:{p.stderr}"
            )
        return p.stdout

    def request(self, request: str):
        return self.run([self.niri_path, "msg", request])

    def get_keyboard_recording(self):
        return self.request("keyboard-recording")

    def run_with_stdin(self, stdin: str):
        return self.run([self.niri_path, "--stdin"], stdin=stdin)


def main():
    if len(sys.argv) != 2:
        raise ValueError("Pass number of seconds to sleep")

    delay = int(sys.argv[1])
    niri = Niri(niri_bin)
    recording = niri.get_keyboard_recording().splitlines()

    if recording[0] != "Keyboard recording:":
        raise ValueError(f"unexepcted output: `{recording[0]}`")
    recording = recording[1:]
    time.sleep(delay)

    stdin = "niri msg action playback-keyboard-recording-once\n" * len(recording)
    niri.run_with_stdin(stdin)


if __name__ == "__main__":
    main()
