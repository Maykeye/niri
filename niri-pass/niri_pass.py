#!/usr/bin/env python
import getpass
import os
import subprocess
from prompt_toolkit import prompt
from pathlib import Path
from dataclasses import dataclass, field, asdict
import tempfile
from typing import Callable, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import sys
import json
import shutil
import datetime
import copy
from colorama import Fore, Style
from niri_keymap import encode_string

N_SALT = 16
ALLOC_ID = -100
passwords_file_path = Path(
    "~/Documents/niri-passes.dat" if len(sys.argv) == 1 else sys.argv[1]
).expanduser()

niri_bin = os.getenv("NIRI_BIN") or "niri"
editor = os.getenv("EDITOR") or "nvim"


def time_utc_str(time: Optional[datetime.datetime] = None):
    if time is None:
        time = datetime.datetime.now(datetime.UTC)
    else:
        time = time.astimezone(datetime.UTC)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Entry:
    id: int
    name: str
    notes: str
    keycode: str
    user_name: str = ""
    user_name_keycode: str = ""
    created_utc: str = field(default_factory=lambda: time_utc_str())
    hidden: bool = False
    history: list[int] = field(default_factory=lambda: [])
    redo: list[int] = field(default_factory=lambda: [])

    def clone(self):
        return copy.deepcopy(self)


@dataclass
class State:
    entries: list[Entry] = field(default_factory=lambda: [])
    next_id: int = 1

    # Storage data
    key: bytes = b""
    salt: bytes = b""

    # Runtime changes
    changed: bool = False

    def init_from_dict(self, data: dict):
        self.next_id = data["next_id"]

        def cleanup(d):
            # if "original_id" in d:
            #    del d["original_id"]
            return d

        self.entries = [Entry(**cleanup(entry)) for entry in data["entries"]]

    def as_dict(self):
        return {
            "next_id": self.next_id,
            "entries": [asdict(entry) for entry in self.entries],
        }

    def get(self, entry_id: int) -> Optional[Entry]:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def alloc_id(self):
        id, self.next_id = self.next_id, self.next_id + 1
        return id

    def append(self, entry: Entry):
        if entry.id == ALLOC_ID:
            entry.id = self.alloc_id()
        self.entries.append(entry)
        self.changed = True

    def branch(self, original: Entry):
        clone = original.clone()
        clone.id = ALLOC_ID
        self.append(clone)
        original.hidden = True
        original.redo.append(clone.id)
        clone.history.append(original.id)
        clone.redo = []

        return clone


class Niri:
    def __init__(self, niri_path) -> None:
        self.niri_path = niri_path

    def run(self, args: list[str]):
        p = subprocess.run(
            args,
            timeout=1,
            capture_output=True,
            text=True,
        )
        if p.returncode != 0 or p.stderr:
            raise subprocess.SubprocessError(
                f"Niri failed: return-code: {p.returncode}, stderr:{p.stderr}"
            )
        return p.stdout

    def request(self, request: str):
        return self.run([self.niri_path, "msg", request])

    def action(self, action: str, *args):
        return self.run([self.niri_path, "msg", "action", action, *args])

    def reset_keyboard_recording(self):
        return self.action("reset-keyboard-recording")

    def start_keyboard_recording(self):
        return self.action("start-keyboard-recording")

    def stop_keyboard_recording(self):
        return self.action("stop-keyboard-recording")

    def extend_keyboard_recording(self, data):
        return self.action("extend-keyboard-recording", data)

    def get_keyboard_recording(self):
        return self.request("keyboard-recording")


def ask_keystring(is_secret: bool, prompt_text: str):
    niri = Niri(niri_bin)
    niri.reset_keyboard_recording()
    if is_secret:
        raw = getpass.getpass(prompt_text)
    else:
        raw = prompt(prompt_text)

    encoded = encode_string(raw)
    return raw, encoded


def impl_edit_text(name: str, notes: str):
    dir = os.getenv("XDG_RUNTIME_DIR")
    fd, path = tempfile.mkstemp(dir=dir, text=True)
    os.write(fd, f"{name}\n{notes}".encode())
    os.close(fd)
    subprocess.run([editor, path])

    lines = Path(path).read_text().splitlines()
    os.unlink(path)
    if not lines or not lines[0].strip() or lines[0].strip().startswith("##"):
        print("Aborted: no entry name")
        return None, None
    name = lines[0].strip()
    notes = "\n".join([line for line in lines[1:] if not line.startswith("##")]).strip()
    return name.strip(), notes.strip()


def add(state: State):
    name, notes = impl_edit_text(
        "## NAME", "## DESCRIPTION(lines with ## will be ignored)"
    )
    if not name or notes is None:
        return

    user_name, user_name_kc = ask_keystring(False, "Username(may be empty): ")
    _, password_kc = ask_keystring(True, "Password: ")
    if not password_kc:
        print("Aborted: no password")
        return
    state.append(
        Entry(
            id=ALLOC_ID,
            name=name,
            notes=notes,
            keycode=password_kc,
            user_name=user_name,
            user_name_keycode=user_name_kc,
        )
    )


def edit_text(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return

    name, notes = impl_edit_text(entry.name, entry.notes)
    if not name or notes is None:
        return

    if entry.name == name and notes == entry.notes:
        print("Aborted: nothing was changed")
        return

    branch = state.branch(entry)
    branch.name = name
    branch.notes = notes
    print(f"Updated `{entry.name}@{entry.id}`; new_id: {branch.id}\n")


def edit_username(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return
    print(f"\nEditing username for {entry.name}")
    user_name, user_name_kc = ask_keystring(
        False, "Username(may be empty; Ctrl-D for abort): "
    )
    if user_name == entry.user_name and entry.user_name_keycode == user_name_kc:
        print("Aborted: nothing was changed")
        return
    branch = state.branch(entry)
    branch.user_name = user_name
    branch.user_name_keycode = user_name_kc
    print(f"Updated `{entry.name}@{entry.id}`; new_id: {branch.id}\n")


def edit_password(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return
    print(f"\nEditing PASSWORD for {entry.name}")
    _, password_kc = ask_keystring(True, "Password(Ctrl-D for abort): ")
    if password_kc == entry.keycode:
        print("Aborted: nothing was changed")
        return
    branch = state.branch(entry)
    branch.keycode = password_kc
    print(f"Updated {entry.name} -> {branch.name}; new id: {branch.id}\n")


def save(state: State):
    raw = json.dumps(state.as_dict())
    fernet = Fernet(state.key)
    assert len(state.salt) == N_SALT
    data = state.salt + fernet.encrypt(raw.encode())

    dir = os.getenv("XDG_RUNTIME_DIR")
    fd, path = tempfile.mkstemp(dir=dir)
    os.close(fd)

    Path(path).write_bytes(data)
    shutil.move(path, passwords_file_path)
    state.changed = False
    print("Saved")


def init_key(state: State, salt: Optional[bytes]):
    niri = Niri(niri_bin)
    niri.reset_keyboard_recording()
    password_s = getpass.getpass("Password for the file: ")
    if not salt:
        salt = os.urandom(N_SALT)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=1_200_000
    )
    password = password_s.encode()
    state.key = base64.urlsafe_b64encode(kdf.derive(password))
    state.salt = salt


def load(state: State):
    data = passwords_file_path.read_bytes()
    salt, data = data[:N_SALT], data[N_SALT:]
    init_key(state, salt)
    fernet = Fernet(state.key)
    text = fernet.decrypt(data).decode()
    as_dict = json.loads(text)
    state.init_from_dict(as_dict)
    print(f"Loaded {passwords_file_path} with {len(state.entries)} entries")


def quit(state: State):
    if state.changed:
        confirmation = prompt(
            "There are unsaved changed. Are you sure you want to exit?\n"
            "Type `YES` (uppercase) to confirm: "
        )
        if confirmation != "YES":
            print("Exit cancelled")
            return False
    return True


def trunc(s: str, n: int):
    s = s.replace("\n", "\\n")
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def fits_filter_smartcase(filter: str, haystack: str):
    if filter.islower():
        return filter in haystack.lower()
    return filter in haystack


def format_entry_data(
    is_hidden: str | bool, id: str | int, name: str, user: str, desc: str
):
    if isinstance(is_hidden, bool):
        is_hidden = "-" if is_hidden else " "
    id = trunc(str(id), 6)
    name = trunc(str(name), 20)
    user = trunc(user, 20)
    desc = trunc(str(desc), 50)

    print(f"{is_hidden}|{id:>6}|{name:20}|{user:20}|{desc}")


def format_entry_separator():
    format_entry_data("#", "#" * 6, "#" * 20, "#" * 20, "#" * 50)


def listing(state: State, filter: str, show_normal: bool, show_hidden: bool):
    format_entry_data("S", "id", "name", "username", "desc")
    found = 0
    for entry in state.entries:
        if entry.hidden and not show_hidden:
            continue
        if not entry.hidden and not show_normal:
            continue
        if (
            fits_filter_smartcase(filter, entry.name)
            or fits_filter_smartcase(filter, entry.user_name)
            or fits_filter_smartcase(filter, entry.notes)
        ):
            status = "-" if entry.hidden else " "
            format_entry_data(
                status, entry.id, entry.name, entry.user_name, entry.notes
            )
            found += 1
    print(f"Found {found} entries.\n")


def list_history(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"Can't find entry by {filter}")
        return

    format_entry_data("S", "id", "name", "username", "desc")
    status = "-" if entry.hidden else " "
    format_entry_data(status, entry.id, entry.name, entry.user_name, entry.notes)
    format_entry_separator()

    def print_other(ids):
        found = 0
        for id in ids:
            history = state.get(id)
            if not history:
                format_entry_data("?", id, "<not found>", "<not found>", "<not found>")
                continue
            format_entry_data(
                history.hidden,
                history.id,
                history.name,
                history.user_name,
                history.notes,
            )
            found += 1
        return found

    found = print_other(entry.history)
    format_entry_separator()
    redos = print_other(entry.redo)
    print(f"Found {found} historical entries and {redos} redo entries.\n")


def get_only_entry(state, filter: str):
    if not filter:
        return None
    # filter by id
    if filter.isdigit():
        return state.get(int(filter))

    def find_unique_by(desc, key: Callable[[Entry], str]):
        fit = [
            entry
            for entry in state.entries
            if not entry.hidden and fits_filter_smartcase(filter, key(entry))
        ]
        if len(fit) == 1:
            return fit[0]
        if len(fit) > 1:
            raise ValueError(f"too many {desc} fits for {filter}")
        return None

    if entry := find_unique_by("name", lambda x: x.name):
        return entry
    if entry := find_unique_by("notes", lambda x: x.notes):
        return entry
    if entry := find_unique_by("username", lambda x: x.user_name):
        return entry
    return None


def send_password(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return
    print(f"\nSending {Style.BRIGHT}{Fore.RED}password{Style.RESET_ALL} {entry.name}")
    niri = Niri(niri_bin)
    niri.reset_keyboard_recording()
    niri.extend_keyboard_recording(entry.keycode)
    print(
        f"Keycodes sent to Niri buffer. Now press your Niri paste shortcut to use it\n"
    )


def send_username(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return
    if not entry.user_name_keycode:
        print(f"No username found for '{entry.name}'")
        return
    print(
        f"\nSending {Style.BRIGHT}{Fore.WHITE}username{Style.RESET_ALL} for {entry.name}"
    )
    niri = Niri(niri_bin)
    niri.reset_keyboard_recording()
    niri.extend_keyboard_recording(entry.user_name_keycode)
    print(
        f"Keycodes sent to Niri buffer. Now press your Niri paste shortcut to use it\n"
    )


def format_entry(entry: Entry):
    format_entry_data(
        entry.hidden,
        entry.id,
        entry.name,
        entry.user_name,
        entry.notes,
    )


def impl_undo_redo(
    state: State, filter: str, desc: str, ids_key: Callable[[Entry], list[int]]
):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"No unique entry found for '{filter}'")
        return
    if entry.hidden:
        print(f"'{entry.name}'@{entry.id} is not active")
        return

    ids = ids_key(entry)
    if not ids:
        print(f"{desc} history not found for '{entry.name}'@{entry.id}")
        return
    format_entry(entry)
    print(f"--- {desc} to -->")
    for id in ids:
        history = state.get(id)
        if not history:
            format_entry_data("?", id, "<not found>", "<not found>", "<not found>")
        else:
            format_entry(history)
    id_s = prompt(f"{desc} id: ")
    if not id_s:
        print("Aborted\n")
        return
    try:
        id = int(id_s)
    except ValueError:
        print(f"Aborted: invalid number {id_s}\n")
        return

    if id not in ids:
        print(f"Aborted: id {id} is not part of the {desc} history\n")
        return

    history = state.get(id)
    if not history:
        print(
            f"Aborted: id {id} is part of the {desc} history but doesn't exist in DB\n"
        )
        return

    entry.hidden = True
    history.hidden = False
    state.changed = True
    print(
        f"Undo: active entry changed from `{entry.name}`@{entry.id} to `{history.name}`@{history.id}\n"
    )


def undo(state: State, filter: str):
    impl_undo_redo(state, filter, "undo", lambda e: e.history)


def redo(state: State, filter: str):
    impl_undo_redo(state, filter, "redo", lambda e: e.redo)


def delete(state: State, filter: str):
    entry = get_only_entry(state, filter)
    if not entry:
        print(f"Aborted: No unique entry found for '{filter}'")
        return
    if entry.hidden:
        print(f"Aborted: '{entry.name}'@{entry.id} is not active")
        return
    format_entry(entry)
    confirm = prompt("Delete? (y/yes): ")
    if confirm.lower() not in ["y", "yes"]:
        print("Cancelled")
        return

    entry.hidden = True
    state.changed = True


def undelete(state: State, filter: str):
    entry = get_only_entry(state, filter)  # only ID will be accepted
    if not entry:
        print(f"Aborted: No unique entry found for '{filter}'")
        return
    if not entry.hidden:
        print(f"Aborted: '{entry.name}'@{entry.id} is active")
        return
    format_entry(entry)
    confirm = prompt("Undelete? (y/yes): ")
    if confirm.lower() not in ["y", "yes"]:
        print("Cancelled")
        return

    entry.hidden = False
    state.changed = True


def encode(s: str):
    kc = encode_string(s)
    niri = Niri(niri_bin)
    niri.reset_keyboard_recording()
    niri.extend_keyboard_recording(kc)
    print(
        f"Keycodes sent to Niri buffer. Now press your Niri paste shortcut to use it\n"
    )


def help():
    print(
        "\n"
        "?: this help\n"
        "A: add\n"
        "L[ah]: list(l - normal, la - all, lh - hidden)\n"
        "E[tup]: edit(txt/usr/pwd)\n"
        "H: list entry history\n"
        "DEL: mark entry as hidden\n"
        "UNDEL: mark entry as visible\n"
        "UNDO: undo entry\n"
        "REDO: redo entry\n"
        "ENC: encode the argument and send it to the buffer\n"
        "U: send username to the niri buffer\n"
        "P: send PASSWORD to buffer\n"
        "S: save\n"
        "Q: quit\n"
    )


def main():
    print(f"Working with {passwords_file_path}")
    state = State()
    if passwords_file_path.exists():
        load(state)
    else:
        print(f"{passwords_file_path} doesn't exist")
        init_key(state, None)

    while True:
        raw_cmd = prompt("Command(`?` for help): ")
        parts = raw_cmd.split(maxsplit=1)
        if not parts or not parts[0]:
            continue
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        try:
            if cmd == "?":
                help()
            elif cmd == "a":
                add(state)
            elif cmd == "la":
                listing(state, arg, show_hidden=True, show_normal=True)
            elif cmd == "lh":
                listing(state, arg, show_hidden=True, show_normal=False)
            elif cmd == "l":
                listing(state, arg, show_hidden=False, show_normal=True)
            elif cmd == "s":
                save(state)
            elif cmd == "p":
                send_password(state, arg)
            elif cmd == "u":
                send_username(state, arg)
            elif cmd == "enc":
                encode(arg)
            elif cmd == "del":
                delete(state, arg)
            elif cmd == "undel":
                undelete(state, arg)
            elif cmd == "et":
                edit_text(state, arg)
            elif cmd == "eu":
                edit_username(state, arg)
            elif cmd == "ep":
                edit_password(state, arg)
            elif cmd == "h":
                list_history(state, arg)
            elif cmd == "undo":
                undo(state, arg)
            elif cmd == "redo":
                redo(state, arg)
            elif cmd == "q":
                if quit(state):
                    return
            else:
                raise ValueError(f"Unknown command {cmd} with {arg=}")
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
