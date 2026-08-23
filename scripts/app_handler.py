"""Launch and stop the exact processes created for each VoidLauncher profile."""

import ctypes
import os
from pathlib import Path
import subprocess
from threading import RLock
import time

import json_reader
from pyvda import AppView, VirtualDesktop


# ============================================================
# PROCESS TRACKING
# ============================================================

# Popen objects identify the exact processes VoidLauncher started.
# Never close processes merely because they have the same executable name.
_profile_processes = {}

_process_lock = RLock()

# Windows message used to request a normal application shutdown.
WM_CLOSE = 0x0010


# ============================================================
# APPLICATION LAUNCHING
# ============================================================

def _normalise_app_entry(entry):
    """Turn a string or JSON object into a Popen command list."""

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


def launch_profile_environment(profile_data):
    """
    Launch enabled apps for a profile.

    Apps are launched after engine.py has already switched
    to the personality's virtual desktop.
    """

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
            process
            for process in _profile_processes.get(
                profile_name,
                []
            )
            if process.poll() is None
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

                process = subprocess.Popen(
                    command,
                    cwd=str(
                        executable.parent
                    ),
                    shell=False
                )

            except OSError as error:

                print(
                    f"[App Handler] Could not start "
                    f"'{executable}': {error}"
                )

                continue

            launched.append(
                process
            )

            print(
                f"[App Handler] Started "
                f"'{executable.name}' "
                f"(PID {process.pid})."
            )

        _profile_processes[
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


# ============================================================
# WINDOWS / PROCESS CLOSING
# ============================================================

def _get_windows_for_process(process_id):
    """Return visible top-level windows belonging to a process."""

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

        if window_process_id.value == process_id:

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


def _request_process_close(process):
    """Ask all visible windows belonging to a process to close normally."""

    windows = _get_windows_for_process(
        process.pid
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
    """
    Ask a process to close normally and wait for it to exit.

    Applications such as Word can therefore show their normal
    save prompt.
    """

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

    return False


def close_profile_environment(profile_data):
    """
    Close only processes started by this profile.

    Applications are asked to close normally instead
    of being force-killed.
    """

    profile_name = profile_data.get(
        "name"
    )

    if not profile_name:
        return

    with _process_lock:

        processes = _profile_processes.pop(
            profile_name,
            []
        )

    if not processes:

        print(
            f"[App Handler] No tracked apps to close "
            f"for: {profile_name}"
        )

        return

    still_running = []

    for process in processes:

        if process.poll() is not None:
            continue

        try:

            closed = _close_process_normally(
                process
            )

            if closed:

                print(
                    f"[App Handler] Stopped PID "
                    f"{process.pid} for "
                    f"'{profile_name}'."
                )

            else:

                still_running.append(
                    process
                )

                print(
                    f"[App Handler] PID "
                    f"{process.pid} is still running. "
                    f"Left it alone instead of "
                    f"force-closing it."
                )

        except OSError as error:

            still_running.append(
                process
            )

            print(
                f"[App Handler] Could not request "
                f"close for PID {process.pid}: "
                f"{error}"
            )

    if still_running:

        with _process_lock:

            _profile_processes[
                profile_name
            ] = still_running

        print(
            f"[App Handler] '{profile_name}' still has "
            f"{len(still_running)} running app(s)."
        )

    else:

        print(
            f"[App Handler] Deactivated environment: "
            f"{profile_name}"
        )


# ============================================================
# BROWSER DETECTION
# ============================================================

def _find_browser():
    """
    Find an installed browser executable.

    Chrome is preferred, then Edge, then Firefox.
    """

    possible_browsers = [

        # Chrome
        os.path.expandvars(
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
        ),

        os.path.expandvars(
            r"%LocalAppData%\Google\Chrome\Application\chrome.exe"
        ),

        # Edge
        os.path.expandvars(
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
        ),

        # Firefox
        os.path.expandvars(
            r"%ProgramFiles%\Mozilla Firefox\firefox.exe"
        ),

        os.path.expandvars(
            r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"
        )
    ]

    for browser in possible_browsers:

        if os.path.isfile(browser):
            return browser

    return None


def _get_browser_windows():
    """
    Find visible browser windows.

    Returns a list of HWNDs.
    """

    browsers = {
        "chrome.exe",
        "msedge.exe",
        "firefox.exe"
    }

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


# ============================================================
# BROWSER WINDOW MOVING
# ============================================================

def _move_browser_window_to_current_desktop(hwnd):
    """
    Move a browser window onto the currently active
    Windows virtual desktop.
    """

    try:

        current_desktop = (
            VirtualDesktop.current()
        )

        if current_desktop is None:

            print(
                "[App Handler] Could not get "
                "current virtual desktop."
            )

            return False

        browser_view = AppView(
            hwnd
        )

        browser_view.move(
            current_desktop
        )

        print(
            "[App Handler] Moved browser window "
            "to the current virtual desktop."
        )

        return True

    except Exception as error:

        print(
            f"[App Handler] Could not move browser "
            f"window to current desktop: {error}"
        )

        return False


def _open_first_browser_window(url):
    """
    Create one new browser window containing the first URL.

    The window is then moved to the currently active
    virtual desktop.
    """

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

        subprocess.Popen(
            [
                browser,
                "--new-window",
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

            print(
                "[App Handler] Could not find "
                "the new browser window."
            )

            return None

        # Move the entire browser window to the
        # personality desktop.
        _move_browser_window_to_current_desktop(
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

        return new_hwnd

    except Exception as error:

        print(
            f"[App Handler] Could not create browser "
            f"window for '{url}': {error}"
        )

        return None


def _open_browser_tab(browser, url):
    """
    Open a URL as a new tab in the existing browser.

    This intentionally does NOT use --new-window.
    """

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


# ============================================================
# PROFILE TABS
# ============================================================

def open_profile_tabs(profile_name):
    """
    Open all websites configured for a profile.

    IMPORTANT:

    - First URL creates ONE new browser window.
    - Remaining URLs become tabs in that window.
    - The browser window is moved to the currently
      active personality desktop.
    """

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

    # --------------------------------------------------------
    # FIRST URL
    # --------------------------------------------------------

    first_url = urls[0]

    browser_window = (
        _open_first_browser_window(
            first_url
        )
    )

    if browser_window is None:
        return

    # --------------------------------------------------------
    # REMAINING URLS
    # --------------------------------------------------------

    for url in urls[1:]:

        time.sleep(
            0.25
        )

        _open_browser_tab(
            browser,
            url
        )

    print(
        f"[App Handler] Opened {len(urls)} website(s) "
        f"for '{profile_name}' in one browser window."
    )