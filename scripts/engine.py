import keyboard
import json_reader
import app_handler
import system_settings
import winreg

from pathlib import Path

import threading
import time
import sys
import os

import pystray
from PIL import Image

import virtual_desktop


# ============================================================
# CONSOLE
# ============================================================

console_visible = False


def hide_console():
    """Hide the console window if running on Windows."""

    if sys.platform == "win32":

        import ctypes

        kernel32 = ctypes.WinDLL(
            "kernel32"
        )

        user32 = ctypes.WinDLL(
            "user32"
        )

        SW_HIDE = 0

        hWnd = kernel32.GetConsoleWindow()

        if hWnd:

            user32.ShowWindow(
                hWnd,
                SW_HIDE
            )

            global console_visible

            console_visible = False


def show_console():
    """Show the console window if running on Windows."""

    if sys.platform == "win32":

        import ctypes

        kernel32 = ctypes.WinDLL(
            "kernel32"
        )

        user32 = ctypes.WinDLL(
            "user32"
        )

        SW_SHOW = 5

        hWnd = kernel32.GetConsoleWindow()

        if hWnd:

            user32.ShowWindow(
                hWnd,
                SW_SHOW
            )

            global console_visible

            console_visible = True


def toggle_console():
    """Toggle console visibility."""

    global console_visible

    if console_visible:

        hide_console()

    else:

        show_console()


# ============================================================
# PERSONALITY TRIGGER
# ============================================================

def handle_shortcut_trigger(
    profile_data
):
    """Activate or deactivate a personality."""

    profile_name = profile_data[
        "name"
    ]

    active_environments = (
        json_reader.get_active_personalities()
    )

    # ========================================================
    # CLOSE PERSONALITY
    # ========================================================

    if profile_name in active_environments:

        print(
            f"[Engine] Closing personality: "
            f"{profile_name}"
        )

        # ----------------------------------------------------
        # Close apps while still on personality desktop.
        # ----------------------------------------------------

        app_handler.close_profile_environment(
            profile_data
        )

        # ----------------------------------------------------
        # Restore system settings.
        # ----------------------------------------------------

        system_settings.restore_profile_settings(
            profile_name
        )

        # ----------------------------------------------------
        # Switch back and delete the desktop if
        # Void Launcher created it.
        # ----------------------------------------------------

        virtual_desktop.restore_previous_desktop(
            profile_name
        )

        # ----------------------------------------------------
        # Mark personality inactive.
        # ----------------------------------------------------

        json_reader.set_personality_state(
            profile_name,
            is_active=False
        )

        print(
            f"[Engine] Closed personality: "
            f"{profile_name}"
        )

        return

    # ========================================================
    # OPEN PERSONALITY
    # ========================================================

    print(
        f"[Engine] Opening personality: "
        f"{profile_name}"
    )

    # --------------------------------------------------------
    # Mark active.
    # --------------------------------------------------------

    json_reader.set_personality_state(
        profile_name,
        is_active=True
    )

    # --------------------------------------------------------
    # 1. SWITCH DESKTOP FIRST.
    # --------------------------------------------------------

    desktop_switched = (
        virtual_desktop.switch_to_profile_desktop(
            profile_data
        )
    )

    # --------------------------------------------------------
    # 2. Launch applications.
    # --------------------------------------------------------

    app_handler.launch_profile_environment(
        profile_data
    )

    # --------------------------------------------------------
    # 3. Open browser windows.
    #
    # This happens AFTER the desktop switch.
    # app_handler.py then explicitly moves each
    # new browser window onto this desktop.
    # --------------------------------------------------------

    app_handler.open_profile_tabs(
        profile_name
    )

    # --------------------------------------------------------
    # 4. Apply system settings.
    # --------------------------------------------------------

    system_settings.apply_profile_settings(
        profile_data
    )

    print(
        f"[Engine] Opened personality: "
        f"{profile_name}"
    )


# ============================================================
# HOTKEY REGISTRATION
# ============================================================

def register_profile_hotkeys():
    """Register enabled profile shortcuts."""

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
                        handle_shortcut_trigger(p)
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
    """Remove registered profile hotkeys."""

    for hotkey_handle in hotkey_handles:

        try:

            keyboard.remove_hotkey(
                hotkey_handle
            )

        except KeyError:
            pass


# ============================================================
# HOTKEY LISTENER
# ============================================================

def start_hotkey_listener(
    stop_event
):
    """Run the profile hotkey listener."""

    hotkey_handles = (
        register_profile_hotkeys()
    )

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


# ============================================================
# TRAY ICON
# ============================================================

def setup_tray_icon(
    stop_event
):
    """Set up and run the system tray icon."""

    icon_path = (
        Path(__file__).parent.parent
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


# ============================================================
# SETTINGS
# ============================================================

def launch_settings():
    """Launch the VoidLauncherUI.exe."""

    try:

        ui_path = (
            Path(__file__).parent.parent
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


# ============================================================
# MAIN
# ============================================================

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

        startup_path = str(
            Path(__file__).resolve()
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