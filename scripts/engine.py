import keyboard
import json_reader
import app_handler
import system_settings
import winreg

from pathlib import Path
from collections import deque

import threading
import time
import sys
import os

import pystray
from PIL import Image

import virtual_desktop


class _ConsoleStream:
    # A stdout/stderr sink that buffers output and attaches to a live console

    def __init__(self, max_lines=4000):
        self._buffer = deque(maxlen=max_lines)
        self._live = None

    def attach(self, live_stream):
        self._live = live_stream
        try:
            live_stream.write("".join(self._buffer))
            live_stream.flush()
        except Exception:
            pass

    def detach(self):
        try:
            if self._live is not None:
                self._live.flush()
                self._live.close()
        except Exception:
            pass
        self._live = None

    def write(self, text):
        try:
            self._buffer.append(text)
            if self._live is not None:
                self._live.write(text)
                self._live.flush()
        except Exception:
            pass
        return len(text)

    def flush(self):
        try:
            if self._live is not None:
                self._live.flush()
        except Exception:
            pass

    def isatty(self):
        return False


# In a --noconsole build there is no console at start. Route output through
# the logging stream so print() never crashes and startup logs are kept.
_console_stream = _ConsoleStream()

sys.stdout = _console_stream
sys.stderr = _console_stream


def _base_path():
    # Return the project root whether running as script or frozen exe
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


# CONSOLE

console_visible = False


def hide_console():
    # Destroy any console window

    if sys.platform == "win32":

        import ctypes

        kernel32 = ctypes.WinDLL(
            "kernel32"
        )

        kernel32.FreeConsole()

        _console_stream.detach()

        global console_visible

        console_visible = False


def show_console():
    # Create a fresh console window and replay buffered logs into it

    if sys.platform == "win32":

        import ctypes

        kernel32 = ctypes.WinDLL(
            "kernel32"
        )

        kernel32.AllocConsole()

        live_stream = None

        try:

            live_stream = open(
                "CONOUT$",
                "w",
                encoding="utf-8",
                buffering=1
            )

        except Exception:

            live_stream = None

        if live_stream is not None:

            _console_stream.attach(
                live_stream
            )

        global console_visible

        console_visible = True


def toggle_console():
    # Toggle console visibility

    if console_visible:

        hide_console()

    else:

        show_console()


# PERSONALITY TRIGGER

def _schedule_desktop_reassert(profile_name, delay=3.0):
    # Re-assert the personality desktop shortly after it opens

    def _later():

        time.sleep(
            delay
        )

        if (
            profile_name
            not in json_reader.get_active_personalities()
        ):
            return

        profile = (
            json_reader.get_personality_by_name(
                profile_name
            )
        )

        if profile is None:
            return

        try:

            virtual_desktop.switch_to_profile_desktop(
                profile
            )

        except Exception as error:

            print(
                f"[Engine] Delayed desktop re-assert "
                f"failed for '{profile_name}': "
                f"{error!r}"
            )

    threading.Thread(
        target=_later,
        daemon=True
    ).start()


def handle_shortcut_trigger(
    profile_data
):
    # Activate or deactivate a personality

    profile_name = profile_data[
        "name"
    ]

    active_environments = (
        json_reader.get_active_personalities()
    )

    # CLOSE PERSONALITY

    if profile_name in active_environments:

        print(
            f"[Engine] Closing personality: "
            f"{profile_name}"
        )

        # Close apps while still on personality desktop.

        try:

            app_handler.close_profile_environment(
                profile_data
            )

        except Exception as error:

            print(
                f"[Engine] Closing apps failed for "
                f"'{profile_name}': {error!r}"
            )

        # Restore system settings.

        try:

            system_settings.restore_profile_settings(
                profile_name
            )

        except Exception as error:

            print(
                f"[Engine] Restoring system settings "
                f"failed for '{profile_name}': {error!r}"
            )

        # Switch back and delete the desktop if Void Launcher created it.

        try:

            virtual_desktop.restore_previous_desktop(
                profile_name
            )

        except Exception as error:

            print(
                f"[Engine] Desktop restore failed for "
                f"'{profile_name}': {error!r}"
            )

        # Mark personality inactive.

        json_reader.set_personality_state(
            profile_name,
            is_active=False
        )

        print(
            f"[Engine] Closed personality: "
            f"{profile_name}"
        )

        return

    # OPEN PERSONALITY

    print(
        f"[Engine] Opening personality: "
        f"{profile_name}"
    )

    # Mark active.

    json_reader.set_personality_state(
        profile_name,
        is_active=True
    )

    # 1. SWITCH DESKTOP FIRST.

    try:

        virtual_desktop.switch_to_profile_desktop(
            profile_data
        )

    except Exception as error:

        print(
            f"[Engine] Desktop switch failed for "
            f"'{profile_name}': {error!r}"
        )

    # 2. Launch applications.

    try:

        app_handler.launch_profile_environment(
            profile_data
        )

    except Exception as error:

        print(
            f"[Engine] App launching failed for "
            f"'{profile_name}': {error!r}"
        )

    # 3. Open browser windows after the desktop switch (moved onto this desktop).

    try:

        app_handler.open_profile_tabs(
            profile_name
        )

    except Exception as error:

        print(
            f"[Engine] Opening tabs failed for "
            f"'{profile_name}': {error!r}"
        )

    # 4. Apply system settings.

    try:

        system_settings.apply_profile_settings(
            profile_data
        )

    except Exception as error:

        print(
            f"[Engine] Applying system settings failed "
            f"for '{profile_name}': {error!r}"
        )

    # A browser (especially Edge) may still pull focus to another
    # desktop a moment after opening. Put focus back and keep it.
    _schedule_desktop_reassert(
        profile_name
    )

    print(
        f"[Engine] Opened personality: "
        f"{profile_name}"
    )


# HOTKEY REGISTRATION

def _safe_shortcut_trigger(profile_data):
    # Run handle_shortcut_trigger without killing the keyboard hook thread

    profile_name = (
        profile_data.get(
            "name",
            "Unknown profile"
        )
    )

    try:

        handle_shortcut_trigger(
            profile_data
        )

    except Exception as error:

        print(
            f"[Engine] Shortcut failed for "
            f"'{profile_name}': {error!r}"
        )


def register_profile_hotkeys():
    # Register enabled profile shortcuts

    profiles = (
        json_reader.get_all_personalities()
    )

    registered_shortcuts = set()

    hotkey_handles = []

    for profile in profiles:

        if not profile.get(
            "enabled",
            False
        ):
            continue

        profile_name = profile.get(
            "name",
            "Unnamed profile"
        )

        shortcut = profile.get(
            "trigger-shortcut",
            ""
        ).strip()

        if not shortcut:
            continue

        shortcut_key = shortcut.casefold()

        if shortcut_key in registered_shortcuts:

            print(
                f"Skipped hotkey for "
                f"'{profile_name}': "
                f"'{shortcut}' is already used "
                f"by another profile."
            )

            continue

        try:

            hotkey_handle = (
                keyboard.add_hotkey(
                    shortcut,
                    lambda p=profile:
                        _safe_shortcut_trigger(p)
                )
            )

            hotkey_handles.append(
                hotkey_handle
            )

            registered_shortcuts.add(
                shortcut_key
            )

            print(
                f"Registered hotkey: "
                f"[{shortcut}] -> linked to "
                f"'{profile_name}'"
            )

        except (
            KeyError,
            ValueError,
            TypeError
        ) as error:

            print(
                f"Skipped invalid hotkey for "
                f"'{profile_name}' "
                f"({shortcut!r}): {error}"
            )

        except Exception as error:

            print(
                f"Could not register hotkey for "
                f"'{profile_name}' "
                f"({shortcut!r}): {error}"
            )

    return hotkey_handles


def unregister_profile_hotkeys(
    hotkey_handles
):
    # Remove registered profile hotkeys

    for hotkey_handle in hotkey_handles:

        try:

            keyboard.remove_hotkey(
                hotkey_handle
            )

        except KeyError:
            pass


# HOTKEY LISTENER

def start_hotkey_listener(
    stop_event
):
    # Run the profile hotkey listener

    try:

        hotkey_handles = (
            register_profile_hotkeys()
        )

        print(
            f"[Engine] Registered "
            f"{len(hotkey_handles)} "
            f"profile hotkey(s)."
        )

    except Exception as error:

        print(
            f"[Engine] Failed to register "
            f"profile hotkeys: {error!r}"
        )

        hotkey_handles = []

    config_revision = (
        json_reader.get_config_revision()
    )

    while not stop_event.is_set():

        time.sleep(
            0.25
        )

        updated_revision = (
            json_reader.get_config_revision()
        )

        if updated_revision != config_revision:

            unregister_profile_hotkeys(
                hotkey_handles
            )

            hotkey_handles = (
                register_profile_hotkeys()
            )

            config_revision = (
                updated_revision
            )

            print(
                "Reloaded profile hotkeys "
                "after configuration change."
            )

    unregister_profile_hotkeys(
        hotkey_handles
    )

    print(
        "Hotkey listener stopped."
    )


# TRAY ICON

def setup_tray_icon(
    stop_event
):
    # Set up and run the system tray icon

    icon_path = (
        _base_path()
        / "UI"
        / "VL_Logo.ico"
    )

    if not icon_path.exists():

        image = Image.new(
            "RGB",
            (64, 64),
            color="blue"
        )

    else:

        image = Image.open(
            icon_path
        )

    icon_ref = [None]

    def create_menu():

        return pystray.Menu(

            pystray.MenuItem(
                "Open Settings",
                lambda icon, item:
                    launch_settings()
            ),

            pystray.MenuItem(
                "Hide Console"
                if console_visible
                else "Show Console",

                lambda icon, item:
                    toggle_console_and_update_menu(
                        icon,
                        item
                    )
            ),

            pystray.MenuItem(
                "Close",

                lambda icon, item:
                    on_exit(
                        icon,
                        stop_event
                    )
            )
        )

    def toggle_console_and_update_menu(
        icon,
        item
    ):

        toggle_console()

        if icon_ref[0] is not None:

            icon_ref[0].menu = (
                create_menu()
            )

    def on_exit(
        icon,
        stop_event
    ):

        print(
            "[Engine] Exit button clicked!"
        )

        print(
            "[Engine] Exiting..."
        )

        close_settings_window()

        stop_event.set()

        print(
            "[Engine] Stopping icon..."
        )

        if icon_ref[0] is not None:

            icon_ref[0].stop()

        print(
            "[Engine] Icon stopped."
        )

    icon = pystray.Icon(
        "VoidLauncher",
        image,
        "Void Launcher",
        create_menu()
    )

    icon_ref[0] = icon

    icon.run()


# SETTINGS

def launch_settings():
    # Launch the VoidLauncherUI.exe

    try:

        ui_path = (
            _base_path()
            / "UI"
            / "VoidLauncherUI.exe"
        )

        if ui_path.exists():

            os.startfile(
                str(ui_path)
            )

            print(
                "[Engine] Launched VoidLauncherUI"
            )

        else:

            print(
                f"[Engine] Error: "
                f"VoidLauncherUI.exe not found at "
                f"{ui_path}"
            )

    except Exception as error:

        print(
            f"[Engine] Error launching "
            f"VoidLauncherUI: {error}"
        )


def close_settings_window():
    # Close the VoidLauncherUI settings window if it is open

    try:

        closed = (
            app_handler.close_processes_by_name(
                "VoidLauncherUI.exe"
            )
        )

        if closed:

            print(
                "[Engine] Closed the settings window."
            )

        else:

            print(
                "[Engine] No settings window was open."
            )

    except Exception as error:

        print(
            f"[Engine] Could not close the settings "
            f"window: {error}"
        )


# MAIN

if __name__ == "__main__":

    hide_console()

    run_at_startup = (
        json_reader.get_global_setting(
            "run-at-startup"
        )
    )

    if run_at_startup:

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )

        startup_path = (
            str(Path(sys.executable))
        )

        winreg.SetValueEx(
            key,
            "Void launcher",
            0,
            winreg.REG_SZ,
            startup_path
        )

        winreg.CloseKey(
            key
        )

    else:

        try:

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            winreg.DeleteValue(
                key,
                "Void launcher"
            )

            winreg.CloseKey(
                key
            )

        except FileNotFoundError:

            pass

    stop_event = threading.Event()

    listener_thread = threading.Thread(
        target=start_hotkey_listener,
        args=(stop_event,)
    )

    listener_thread.daemon = True

    listener_thread.start()

    setup_tray_icon(
        stop_event
    )

    listener_thread.join(
        timeout=2.0
    )

    print(
        "Void Launcher Shutdown Complete"
    )
