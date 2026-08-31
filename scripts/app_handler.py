# Launch and stop exactly the processes VoidLauncher opened per profile.

import ctypes
import os
from pathlib import Path
import subprocess
from threading import RLock
import time
import winreg

import json_reader
import virtual_desktop

from pyvda import AppView, VirtualDesktop


# PROCESS TRACKING

# Each entry records EXACTLY what VoidLauncher itself opened:
#   {"kind": "process", "popen": Popen}   - an app process we started
#   {"kind": "window",  "window_id": int} - a browser window we opened
# Closing a personality only closes these - other instances of the
# same application the user already had open are never touched.
_profile_apps = {}

_process_lock = RLock()

# Windows message used to request a normal application shutdown.
WM_CLOSE = 0x0010


# APPLICATION LAUNCHING

def _normalise_app_entry(entry):
    # Turn a string or JSON object into a Popen command list

    if isinstance(entry, str):
        path = entry.strip()
        arguments = []

    elif isinstance(entry, dict):
        path = str(
            entry.get("path", "")
        ).strip()

        arguments = entry.get(
            "arguments",
            []
        )

        if isinstance(arguments, str):
            arguments = [arguments]

        elif not isinstance(arguments, list) or not all(
            isinstance(arg, str)
            for arg in arguments
        ):
            return None

    else:
        return None

    if not path:
        return None

    command = [
        os.path.expandvars(path),
        *arguments
    ]

    # Microsoft Word gets its own process.
    if Path(path).name.casefold() == "winword.exe":
        if "/x" not in [
            arg.casefold()
            for arg in arguments
        ]:
            command.insert(
                1,
                "/x"
            )

    return command


def _register_tracked_process(profile_name, command, cwd=None):
    # Start a process and track it as belonging to the profile

    process = subprocess.Popen(
        command,
        cwd=cwd,
        shell=False
    )

    return {
        "kind": "process",
        "popen": process
    }


def launch_profile_environment(profile_data):
    # Launch enabled apps for a profile

    profile_name = profile_data.get(
        "name"
    )

    if not profile_name:
        print(
            "[App Handler] Could not launch a profile "
            "without a name."
        )
        return

    # Load the latest saved settings.
    app_entries = (
        json_reader.get_enabled_profile_apps(
            profile_name
        )
    )

    with _process_lock:

        running = [
            entry
            for entry in _profile_apps.get(
                profile_name,
                []
            )
            if (
                entry.get("kind") == "process"
                and entry["popen"].poll() is None
            )
        ]

        if running:
            print(
                f"[App Handler] '{profile_name}' already "
                f"has tracked app(s) running."
            )
            return

        launched = []

        for entry in app_entries:

            command = _normalise_app_entry(
                entry
            )

            if command is None:
                print(
                    f"[App Handler] Skipped invalid "
                    f"app entry: {entry!r}"
                )
                continue

            executable = Path(
                command[0]
            )

            if not executable.is_file():
                print(
                    f"[App Handler] App not found, skipped: "
                    f"{command[0]}"
                )
                continue

            if executable.suffix.casefold() == ".lnk":
                print(
                    f"[App Handler] Skipped shortcut "
                    f"(cannot track its real process): "
                    f"{executable}"
                )
                continue

            try:

                entry = _register_tracked_process(
                    profile_name,
                    command,
                    cwd=str(
                        executable.parent
                    )
                )

            except OSError as error:

                print(
                    f"[App Handler] Could not start "
                    f"'{executable}': {error}"
                )

                continue

            launched.append(
                entry
            )

            print(
                f"[App Handler] Started "
                f"'{executable.name}' "
                f"(PID {entry['popen'].pid})."
            )

        _profile_apps[
            profile_name
        ] = launched

    if launched:

        print(
            f"[App Handler] Activated environment: "
            f"{profile_name}"
        )

    else:

        print(
            f"[App Handler] No apps were launched for: "
            f"{profile_name}"
        )


# WINDOWS / PROCESS CLOSING

def _get_windows_for_processes(process_ids):
    # Return visible top-level windows belonging to any given PID

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
            ctypes.byref(
                window_process_id
            )
        )

        if window_process_id.value in process_ids:

            if user32.IsWindowVisible(hwnd):

                windows.append(
                    hwnd
                )

        return True

    user32.EnumWindows(
        EnumWindowsProc(callback),
        0
    )

    return windows


def _process_snapshot():
    # Return a {pid: (parent_pid, executable_name)} snapshot

    kernel32 = ctypes.windll.kernel32

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_wchar * 260)
        ]

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(
        PROCESSENTRY32W
    )

    snapshot = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPPROCESS,
        0
    )

    if snapshot in (0, -1):
        return {}

    result = {}

    try:

        if not kernel32.Process32FirstW(
            snapshot,
            ctypes.byref(entry)
        ):
            return {}

        while True:

            result[
                entry.th32ProcessID
            ] = (
                entry.th32ParentProcessID,
                entry.szExeFile
            )

            if not kernel32.Process32NextW(
                snapshot,
                ctypes.byref(entry)
            ):
                break

    finally:

        kernel32.CloseHandle(
            snapshot
        )

    return result


def _windows_for_process(process_id):
    # Return visible top-level windows belonging to one process

    return _get_windows_for_processes(
        [process_id]
    )


def _force_kill_process(pid):
    # Terminate a single process by PID

    kernel32 = ctypes.windll.kernel32

    handle = kernel32.OpenProcess(
        0x0001,
        False,
        pid
    )

    if not handle:
        return

    try:

        kernel32.TerminateProcess(
            handle,
            1
        )

    except Exception:
        pass

    finally:

        kernel32.CloseHandle(
            handle
        )


def _close_request_windows(process_ids):
    # Ask every visible window of the PIDs to close normally

    user32 = ctypes.windll.user32

    windows = _get_windows_for_processes(
        process_ids
    )

    for hwnd in windows:

        user32.PostMessageW(
            hwnd,
            WM_CLOSE,
            0,
            0
        )

    return bool(windows)


def _request_process_close(process):
    # Ask all visible windows of a process to close normally

    process_id = process.pid

    windows = _windows_for_process(
        process_id
    )

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
    # Ask a process to close normally and wait for it to exit

    if process.poll() is not None:
        return True

    print(
        f"[App Handler] Asking PID "
        f"{process.pid} to close normally..."
    )

    close_requested = _request_process_close(
        process
    )

    if not close_requested:

        print(
            f"[App Handler] No visible window found "
            f"for PID {process.pid}."
        )

        return False

    for _ in range(20):

        if process.poll() is not None:
            return True

        time.sleep(
            0.25
        )

    print(
        f"[App Handler] PID {process.pid} is still "
        f"running. Left it alone instead of "
        f"force-closing it."
    )

    return False


def _close_tracked_window(window_id):
    # Close a browser window VoidLauncher itself opened

    user32 = ctypes.windll.user32

    if not user32.IsWindow(window_id):
        return True

    print(
        f"[App Handler] Closing browser window "
        f"0x{window_id:08X}..."
    )

    user32.PostMessageW(
        window_id,
        WM_CLOSE,
        0,
        0
    )

    for _ in range(12):

        if not user32.IsWindow(window_id):
            return True

        time.sleep(
            0.25
        )

    print(
        f"[App Handler] Browser window "
        f"0x{window_id:08X} is still open. "
        f"Left it alone."
    )

    return False


def _close_tracked_entry(entry):
    # Close exactly one thing VoidLauncher opened for a profile

    if entry["kind"] == "process":

        process = entry["popen"]

        try:

            return _close_process_normally(
                process
            )

        except OSError as error:

            print(
                f"[App Handler] Could not request "
                f"close for PID {process.pid}: "
                f"{error}"
            )

            return False

    if entry["kind"] == "window":

        return _close_tracked_window(
            entry["window_id"]
        )

    return True


def close_profile_environment(profile_data):
    # Close only things this profile actually opened

    profile_name = profile_data.get(
        "name"
    )

    if not profile_name:
        return

    with _process_lock:

        entries = _profile_apps.pop(
            profile_name,
            []
        )

    if not entries:

        print(
            f"[App Handler] No tracked apps to close "
            f"for: {profile_name}"
        )

        return

    remaining = []

    for entry in entries:

        closed = _close_tracked_entry(
            entry
        )

        if closed:

            if entry["kind"] == "process":

                print(
                    f"[App Handler] Stopped PID "
                    f"{entry['popen'].pid} for "
                    f"'{profile_name}'."
                )

        else:

            remaining.append(
                entry
            )

    if remaining:

        with _process_lock:

            _profile_apps[
                profile_name
            ] = remaining

        print(
            f"[App Handler] '{profile_name}' still has "
            f"{len(remaining)} running app(s)."
        )

    else:

        print(
            f"[App Handler] Deactivated environment: "
            f"{profile_name}"
        )


def close_processes_by_name(image_name):
    # Close every process with the given executable name

    image_name = (
        Path(
            image_name
        ).name.casefold()
    )

    def _matching_pids():

        snapshot = _process_snapshot()

        return {
            pid
            for pid, (_, name) in snapshot.items()
            if name.casefold() == image_name
        }

    pids = _matching_pids()

    if not pids:
        return False

    has_windows = _close_request_windows(
        pids
    )

    deadline = time.time() + 2.0

    while time.time() < deadline:

        if not _matching_pids():
            return True

        if not has_windows:
            break

        time.sleep(
            0.25
        )

    for pid in _matching_pids():

        _force_kill_process(
            pid
        )

    return True


# BROWSER DETECTION

def _get_default_browser_path():
    # Resolve the Windows default web browser executable

    try:

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            (
                r"Software\Microsoft\Windows\Shell"
                r"\Associations\UrlAssociations\http"
                r"\UserChoice"
            ),
            0,
            winreg.KEY_READ
        )

        prog_id = winreg.QueryValueEx(
            key,
            "ProgId"
        )[0]

        winreg.CloseKey(key)

    except OSError:
        return None

    if not prog_id:
        return None

    try:

        command = winreg.QueryValue(
            winreg.HKEY_CLASSES_ROOT,
            prog_id + r"\shell\open\command"
        )

    except OSError:
        return None

    if not command:
        return None

    path_part = command.strip()

    # The open command is usually a quoted path, e.g.
    # "C:\Program Files\Mozilla Firefox\firefox.exe" -osint -url "%1"
    if path_part.startswith("\""):

        end = path_part.find("\"", 1)

        if end <= 1:
            return None

        path_part = path_part[1:end]

    else:

        path_part = path_part.split(None, 1)[0]

    path_part = os.path.expandvars(
        path_part
    )

    if os.path.isfile(path_part):
        print(
            f"[App Handler] Default browser: "
            f"{path_part}"
        )
        return path_part

    return None


def _find_browser():
    # Find a browser executable

    default_browser = _get_default_browser_path()

    if default_browser:
        return default_browser

    possible_browsers = [

        # Chrome
        r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
        r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
        r"%LocalAppData%\Google\Chrome\Application\chrome.exe",

        # Edge
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",

        # Firefox
        r"%ProgramFiles%\Mozilla Firefox\firefox.exe",
        r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",

        # Other Chromium forks
        r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%ProgramFiles%\Opera\launcher.exe",
        r"%LocalAppData%\Vivaldi\Application\vivaldi.exe"
    ]

    for browser in possible_browsers:

        browser = os.path.expandvars(
            browser
        )

        if os.path.isfile(browser):
            return browser

    return None


def _get_browser_windows():
    # Find visible browser windows

    browsers = {
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe"
    }

    default_browser = _find_browser()

    if default_browser:
        browsers.add(
            Path(default_browser).name.casefold()
        )

    windows = []

    user32 = ctypes.windll.user32

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p
    )

    def callback(hwnd, _):

        if not user32.IsWindowVisible(hwnd):
            return True

        process_id = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                process_id
            )
        )

        try:

            process_handle = (
                ctypes.windll.kernel32.OpenProcess(
                    0x0410,
                    False,
                    process_id.value
                )
            )

            if not process_handle:
                return True

            buffer = ctypes.create_unicode_buffer(
                260
            )

            size = ctypes.c_ulong(
                260
            )

            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                process_handle,
                0,
                buffer,
                ctypes.byref(
                    size
                )
            )

            ctypes.windll.kernel32.CloseHandle(
                process_handle
            )

            executable_name = Path(
                buffer.value
            ).name.casefold()

            if executable_name in browsers:

                windows.append(
                    hwnd
                )

        except Exception:
            pass

        return True

    user32.EnumWindows(
        EnumWindowsProc(callback),
        0
    )

    return windows


# BROWSER WINDOW MOVING

def _move_browser_window_to_profile_desktop(profile_name, hwnd):
    # Move a browser window onto the personality's virtual desktop

    try:

        personality_desktop = (
            virtual_desktop.get_active_personality_desktop(
                profile_name
            )
        )

        if personality_desktop is None:

            personality_desktop = (
                VirtualDesktop.current()
            )

        if personality_desktop is None:

            print(
                "[App Handler] Could not get "
                "a virtual desktop for the browser."
            )

            return False

        AppView(
            hwnd
        ).move(
            personality_desktop
        )

        print(
            "[App Handler] Moved browser window "
            "onto the personality desktop."
        )

        return True

    except Exception as error:

        print(
            f"[App Handler] Could not move browser "
            f"window onto the personality desktop: "
            f"{error}"
        )

        return False


def _open_first_browser_window(profile_name, url):
    # Create one new browser window containing the first URL

    browser = _find_browser()

    if not browser:

        print(
            "[App Handler] No supported browser "
            "was found."
        )

        return None

    try:

        before = set(
            _get_browser_windows()
        )

        new_window_arg = (
            "-new-window"
            if (
                Path(browser).name.casefold()
                == "firefox.exe"
            )
            else "--new-window"
        )

        subprocess.Popen(
            [
                browser,
                new_window_arg,
                url
            ],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        print(
            f"[App Handler] Opening browser window: "
            f"{url}"
        )

        new_hwnd = None

        for _ in range(50):

            time.sleep(
                0.1
            )

            after = set(
                _get_browser_windows()
            )

            new_windows = (
                after - before
            )

            if new_windows:

                new_hwnd = next(
                    iter(new_windows)
                )

                break

        if new_hwnd is None:

            # The browser handed the URL to an existing window
            # (Edge/Chrome delegation) faster than the launcher
            # could snapshot it. Fall back to pulling every
            # browser window onto the personality desktop.
            print(
                "[App Handler] No brand-new window was "
                "detected; pulling existing browser "
                "windows onto the personality desktop."
            )

            for hwnd in _get_browser_windows():

                _move_browser_window_to_profile_desktop(
                    profile_name,
                    hwnd
                )

            existing = _get_browser_windows()

            if existing:

                new_hwnd = existing[0]

                ctypes.windll.user32.ShowWindow(
                    new_hwnd,
                    5
                )

                ctypes.windll.user32.SetForegroundWindow(
                    new_hwnd
                )

            _reassert_profile_desktop(
                profile_name
            )

            return new_hwnd

        # Track the window itself, so closing the personality asks
        # EXACTLY this window to close - never windows the user
        # already had open in the same browser.
        with _process_lock:

            _profile_apps.setdefault(
                profile_name,
                []
            ).append(
                {
                    "kind": "window",
                    "window_id": new_hwnd
                }
            )

        # Move the browser window onto the personality desktop.
        _move_browser_window_to_profile_desktop(
            profile_name,
            new_hwnd
        )

        # Bring it to the front.
        ctypes.windll.user32.ShowWindow(
            new_hwnd,
            5
        )

        ctypes.windll.user32.SetForegroundWindow(
            new_hwnd
        )

        _reassert_profile_desktop(
            profile_name
        )

        return new_hwnd

    except Exception as error:

        print(
            f"[App Handler] Could not create browser "
            f"window for '{url}': {error}"
        )

        return None


def _open_browser_tab(browser, url):
    # Open a URL as a new tab in the existing browser

    try:

        subprocess.Popen(
            [
                browser,
                url
            ],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        print(
            f"[App Handler] Opened browser tab: "
            f"{url}"
        )

        return True

    except Exception as error:

        print(
            f"[App Handler] Could not open browser tab "
            f"'{url}': {error}"
        )

        return False


def _reassert_profile_desktop(profile_name):
    # Put focus back onto the personality's virtual desktop

    profile = (
        json_reader.get_personality_by_name(
            profile_name
        )
    )

    if profile is None:
        return

    if not profile.get(
        "virtual-desktop-switch",
        {}
    ).get("enabled", False):
        return

    virtual_desktop.switch_to_profile_desktop(
        profile
    )


# PROFILE TABS

def open_profile_tabs(profile_name):
    # Open all websites configured for a profile

    urls = (
        json_reader.get_enabled_profile_tabs(
            profile_name
        )
    )

    if not urls:

        print(
            f"[App Handler] No websites configured "
            f"for '{profile_name}'."
        )

        return

    browser = _find_browser()

    if not browser:

        print(
            "[App Handler] No supported browser "
            "was found."
        )

        return

    # FIRST URL

    first_url = urls[0]

    browser_window = (
        _open_first_browser_window(
            profile_name,
            first_url
        )
    )

    if browser_window is None:
        return

    # REMAINING URLS

    for url in urls[1:]:

        time.sleep(
            0.25
        )

        _open_browser_tab(
            browser,
            url
        )

    # Chrome/Edge can steal the current desktop when they open, and the
    # window move + focus race can finish just AFTER they open. Keep
    # putting the visible desktop back for a couple of seconds so the
    # personality desktop wins - otherwise Edge parks everything on
    # Desktop One and every subsequent app follows it there.
    for _ in range(8):

        _reassert_profile_desktop(
            profile_name
        )

        time.sleep(
            0.25
        )

    print(
        f"[App Handler] Opened {len(urls)} website(s) "
        f"for '{profile_name}' in one browser window."
    )
