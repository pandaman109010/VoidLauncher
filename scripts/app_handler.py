"""Launch and stop the exact processes created for each VoidLauncher profile."""

import os
from pathlib import Path
import subprocess
from threading import RLock

import json_reader


# Popen objects identify the exact processes VoidLauncher started. Never close
# processes merely because they have the same executable name.
_profile_processes = {}
_process_lock = RLock()


def _normalise_app_entry(entry):
    """Turn a string or future JSON object into a Popen command list."""
    if isinstance(entry, str):
        path = entry.strip()
        arguments = []
    elif isinstance(entry, dict):
        path = str(entry.get("path", "")).strip()
        arguments = entry.get("arguments", [])
        if isinstance(arguments, str):
            arguments = [arguments]
        elif not isinstance(arguments, list) or not all(isinstance(arg, str) for arg in arguments):
            return None
    else:
        return None

    if not path:
        return None
    return [os.path.expandvars(path), *arguments]


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
            process for process in _profile_processes.get(profile_name, [])
            if process.poll() is None
        ]
        if running:
            print(f"[App Handler] '{profile_name}' already has tracked app(s) running.")
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
                print(f"[App Handler] Skipped shortcut (cannot track its real process): {executable}")
                continue

            try:
                process = subprocess.Popen(command, cwd=str(executable.parent), shell=False)
            except OSError as error:
                print(f"[App Handler] Could not start '{executable}': {error}")
                continue

            launched.append(process)
            print(f"[App Handler] Started '{executable.name}' (PID {process.pid}).")

        _profile_processes[profile_name] = launched

    if launched:
        print(f"[App Handler] Activated environment: {profile_name}")
    else:
        print(f"[App Handler] No apps were launched for: {profile_name}")


def close_profile_environment(profile_data):
    """Close only processes started by this profile during this engine session."""
    profile_name = profile_data.get("name")
    if not profile_name:
        return

    with _process_lock:
        processes = _profile_processes.pop(profile_name, [])

    if not processes:
        print(f"[App Handler] No tracked apps to close for: {profile_name}")
        return

    for process in processes:
        if process.poll() is not None:
            continue
        try:
            process.terminate()
            process.wait(timeout=3)
            print(f"[App Handler] Stopped PID {process.pid} for '{profile_name}'.")
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"[App Handler] Force-stopped PID {process.pid} for '{profile_name}'.")
        except OSError as error:
            print(f"[App Handler] Could not stop PID {process.pid}: {error}")

    print(f"[App Handler] Deactivated environment: {profile_name}")
