"""Launch and stop the exact processes created for each VoidLauncher profile."""

import ctypes
import os
from pathlib import Path
import subprocess
from threading import RLock
import time
import webbrowser
import json_reader


# Popen objects identify the exact processes VoidLauncher started.
# Never close processes merely because they have the same executable name.
_profile_processes = {}
_process_lock = RLock()

# Windows message used to request a normal application shutdown.
WM_CLOSE = 0x0010


def _normalise_app_entry(entry):
    """Turn a string or JSON object into a Popen command list."""
    if isinstance(entry, str):
        path = entry.strip()
        arguments = []
    elif isinstance(entry, dict):
        path = str(entry.get("path", "")).strip()
        arguments = entry.get("arguments", [])

        if isinstance(arguments, str):
            arguments = [arguments]
        elif not isinstance(arguments, list) or not all(
            isinstance(arg, str) for arg in arguments
        ):
            return None
    else:
        return None

    if not path:
        return None

    command = [os.path.expandvars(path), *arguments]

    if Path(path).name.casefold() == "winword.exe":
        if "/x" not in [arg.casefold() for arg in arguments]:
            command.insert(1, "/x")

    return command


def launch_profile_environment(profile_data):
    """Launch enabled apps for a profile and retain their process handles."""
    profile_name = profile_data.get("name")

    if not profile_name:
        print("[App Handler] Could not launch a profile without a name.")
        return

    # Load the latest saved settings, not the possibly stale hotkey callback.
    app_entries = json_reader.get_enabled_profile_apps(profile_name)

    with _process_lock:
        running = [
            process
            for process in _profile_processes.get(profile_name, [])
            if process.poll() is None
        ]

        if running:
            print(
                f"[App Handler] '{profile_name}' already has tracked app(s) running."
            )
            return

        launched = []

        for entry in app_entries:
            command = _normalise_app_entry(entry)

            if command is None:
                print(f"[App Handler] Skipped invalid app entry: {entry!r}")
                continue

            executable = Path(command[0])

            if not executable.is_file():
                print(f"[App Handler] App not found, skipped: {command[0]}")
                continue

            if executable.suffix.casefold() == ".lnk":
                print(
                    f"[App Handler] Skipped shortcut "
                    f"(cannot track its real process): {executable}"
                )
                continue

            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(executable.parent),
                    shell=False
                )
            except OSError as error:
                print(f"[App Handler] Could not start '{executable}': {error}")
                continue

            launched.append(process)

            print(
                f"[App Handler] Started '{executable.name}' "
                f"(PID {process.pid})."
            )

        _profile_processes[profile_name] = launched

    open_profile_tabs(profile_name)
    if launched:
        print(f"[App Handler] Activated environment: {profile_name}")
    else:
        print(f"[App Handler] No apps were launched for: {profile_name}")
    


def _get_windows_for_process(process_id):
    """Return the visible top-level windows belonging to a process."""
    windows = []

    user32 = ctypes.windll.user32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p
    )

    def callback(hwnd, _):
        window_process_id = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(window_process_id)
        )

        if window_process_id.value == process_id:
            if user32.IsWindowVisible(hwnd):
                windows.append(hwnd)

        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)

    return windows


def _request_process_close(process):
    """Ask all visible windows belonging to a process to close normally."""
    windows = _get_windows_for_process(process.pid)

    if not windows:
        return False

    user32 = ctypes.windll.user32

    for hwnd in windows:
        user32.PostMessageW(
            hwnd,
            WM_CLOSE,
            0,
            0
        )

    return True


def _close_process_normally(process):
    """
    Ask a process to close normally and wait for it to exit.

    This behaves much more like clicking the application's X button.
    Applications such as Word can therefore show their normal save prompt.
    """
    if process.poll() is not None:
        return True

    print(f"[App Handler] Asking PID {process.pid} to close normally...")

    close_requested = _request_process_close(process)

    if not close_requested:
        print(
            f"[App Handler] No visible window found for PID {process.pid}."
        )
        return False

    # Give the application a moment to process the close request.
    #
    # We intentionally do NOT force-kill the process if it takes longer.
    # The user may be looking at a Save/Don't Save/Cancel dialog.
    for _ in range(20):
        if process.poll() is not None:
            return True

        time.sleep(0.25)

    return False


def close_profile_environment(profile_data):
    """
    Close only processes started by this profile during this engine session.

    Applications are asked to close normally instead of being force-killed.
    This allows programs such as Microsoft Word to show their normal
    unsaved-changes prompt.
    """
    profile_name = profile_data.get("name")

    if not profile_name:
        return

    with _process_lock:
        processes = _profile_processes.pop(profile_name, [])

    if not processes:
        print(
            f"[App Handler] No tracked apps to close for: {profile_name}"
        )
        return

    still_running = []

    for process in processes:
        if process.poll() is not None:
            continue

        try:
            closed = _close_process_normally(process)

            if closed:
                print(
                    f"[App Handler] Stopped PID {process.pid} "
                    f"for '{profile_name}'."
                )
            else:
                # IMPORTANT:
                # Do not kill the process.
                #
                # It may be waiting for the user to answer a save dialog.
                still_running.append(process)

                print(
                    f"[App Handler] PID {process.pid} is still running. "
                    f"Left it alone instead of force-closing it."
                )

        except OSError as error:
            still_running.append(process)

            print(
                f"[App Handler] Could not request close for "
                f"PID {process.pid}: {error}"
            )

    # Keep processes that are still alive so Void Launcher can still track
    # them instead of forgetting about them.
    if still_running:
        with _process_lock:
            _profile_processes[profile_name] = still_running

        print(
            f"[App Handler] '{profile_name}' still has "
            f"{len(still_running)} running app(s)."
        )
    else:
        print(
            f"[App Handler] Deactivated environment: {profile_name}"
        )

def open_profile_tabs(profile_name):
    """Open the websites configured for a profile in the default browser."""
    urls = json_reader.get_enabled_profile_tabs(profile_name)

    for url in urls:
        try:
            webbrowser.open(url)
            print(f"[App Handler] Opened website: {url}")
        except Exception as error:
            print(f"[App Handler] Could not open website '{url}': {error}")