import keyboard     #clicky wicky
import json_reader  # readey jsey
import app_handler  #opey clozey
import winreg       #starty warty
from pathlib import Path #findy pathy
import threading
import time
import sys
import os
import pystray
from PIL import Image

# Global variable to track console visibility
console_visible = False

def hide_console():
    """Hide the console window if running in Windows"""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_HIDE = 0
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, SW_HIDE)
            global console_visible
            console_visible = False

def show_console():
    """Show the console window if running in Windows"""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_SHOW = 5
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, SW_SHOW)
            global console_visible
            console_visible = True

def toggle_console():
    """Toggle console visibility"""
    global console_visible
    if console_visible:
        hide_console()
    else:
        show_console()

def handle_shortcut_trigger(profile_data):
    # Listens to the shortkeys and routes the user's custom profile data
    profile_name = profile_data["name"]

    # Grab the current active list from our central reader memory
    active_environments = json_reader.get_active_personalities()

    # Check if its already open, close it
    if profile_name in active_environments:
        json_reader.set_personality_state(profile_name, is_active=False)
        app_handler.close_profile_environment(profile_data)

    # Open the personality
    else:
        json_reader.set_personality_state(profile_name, is_active=True)
        app_handler.launch_profile_environment(profile_data)

def register_profile_hotkeys():
    """Register enabled profile shortcuts and return their keyboard handles."""
    profiles = json_reader.get_all_personalities()
    registered_shortcuts = set()
    hotkey_handles = []

    for profile in profiles:
        if not profile.get("enabled", False):
            continue

        profile_name = profile.get("name", "Unnamed profile")
        shortcut = profile.get("trigger-shortcut", "").strip()

        if not shortcut:
            continue

        shortcut_key = shortcut.casefold()
        if shortcut_key in registered_shortcuts:
            print(f"Skipped hotkey for '{profile_name}': '{shortcut}' is already used by another profile.")
            continue

        try:
            hotkey_handle = keyboard.add_hotkey(
                shortcut,
                lambda p=profile: handle_shortcut_trigger(p),
            )
            hotkey_handles.append(hotkey_handle)
            registered_shortcuts.add(shortcut_key)
            print(f"Registered hotkey: [{shortcut}] -> linked to '{profile_name}'")
        except (KeyError, ValueError, TypeError) as error:
            print(f"Skipped invalid hotkey for '{profile_name}' ({shortcut!r}): {error}")
        except Exception as error:
            print(f"Could not register hotkey for '{profile_name}' ({shortcut!r}): {error}")

    return hotkey_handles

def unregister_profile_hotkeys(hotkey_handles):
    for hotkey_handle in hotkey_handles:
        try:
            keyboard.remove_hotkey(hotkey_handle)
        except KeyError:
            pass

def start_hotkey_listener(stop_event):
    hotkey_handles = register_profile_hotkeys()
    config_revision = json_reader.get_config_revision()

    while not stop_event.is_set():
        time.sleep(0.25)

        # The settings app writes config.json. Re-register only after a
        # successful reload so new, edited, or removed shortcuts work live.
        updated_revision = json_reader.get_config_revision()
        if updated_revision != config_revision:
            unregister_profile_hotkeys(hotkey_handles)
            hotkey_handles = register_profile_hotkeys()
            config_revision = updated_revision
            print("Reloaded profile hotkeys after configuration change.")

    unregister_profile_hotkeys(hotkey_handles)
    print("Hotkey listener stopped.")

def setup_tray_icon(stop_event):
    """Set up and run the system tray icon with the requested 3 buttons"""

    # Get the path to the icon
    icon_path = Path(__file__).parent.parent / "UI" / "VL_Logo.ico"
    if not icon_path.exists():
        # Fallback to a default icon if the custom one isn't found
        # Create a simple icon (this is just a fallback)
        image = Image.new('RGB', (64, 64), color='blue')
    else:
        image = Image.open(icon_path)

    # We'll update the menu dynamically, so we need a reference to the icon object
    # We'll store it in a list so we can modify it inside nested functions
    icon_ref = [None]

    def create_menu():
        return pystray.Menu(
            pystray.MenuItem('Open Settings', lambda icon, item: launch_settings()),
            pystray.MenuItem(
                'Hide Console' if console_visible else 'Show Console',
                lambda icon, item: toggle_console_and_update_menu(icon, item)
            ),
            pystray.MenuItem('Close', lambda icon, item: on_exit(icon, stop_event))
        )

    def toggle_console_and_update_menu(icon, item):
        """Toggle console and update the menu"""
        toggle_console()
        # Update the menu of the existing icon
        if icon_ref[0] is not None:
            icon_ref[0].menu = create_menu()

    def on_exit(icon, stop_event):
        """Handle exit from tray menu"""
        print("[App Handler] Exit button clicked!")
        print("[App Handler] Exiting...")
        # Signal the hotkey listener to stop
        stop_event.set()
        # Stop the icon
        print("[App Handler] Stopping icon...")
        if icon_ref[0] is not None:
            icon_ref[0].stop()
        print("[App Handler] Icon stopped.")

    # Create the icon
    icon = pystray.Icon("VoidLauncher", image, "Void Launcher", create_menu())
    icon_ref[0] = icon

    # Run the icon (this blocks until icon.stop() is called)
    icon.run()

def launch_settings():
    """Launch the VoidLauncherUI.exe from the UI folder"""
    try:
        ui_path = Path(__file__).parent.parent / "UI" / "VoidLauncherUI.exe"
        if ui_path.exists():
            os.startfile(str(ui_path))
            print("[App Handler] Launched VoidLauncherUI")
        else:
            print(f"[App Handler] Error: VoidLauncherUI.exe not found at {ui_path}")
    except Exception as e:
        print(f"[App Handler] Error launching VoidLauncherUI: {e}")

if __name__ == "__main__": #checky if mainy
    # Hide console by default
    hide_console()

    run_at_startup = json_reader.get_global_setting("run-at-startup")
    if run_at_startup:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run", #sceary regy
            0,
            winreg.KEY_SET_VALUE
        )
        startup_path = str(Path(__file__).resolve()) #findy namey and directory
        winreg.SetValueEx(key, "Void launcher", 0, winreg.REG_SZ, startup_path) #set starty
        winreg.CloseKey(key)
    # remove startup
    else:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run", #sceary regy
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "Void launcher") #boop
            winreg.CloseKey(key) #gone
        except FileNotFoundError:
            pass

    # Create a shared event for stopping
    stop_event = threading.Event()

    # Start the hotkey listener in a daemon thread
    listener_thread = threading.Thread(target=start_hotkey_listener, args=(stop_event,))
    listener_thread.daemon = True
    listener_thread.start()

    # Run the tray icon (or console fallback) in the main thread
    setup_tray_icon(stop_event)

    # Wait for the listener thread to finish (with timeout)
    listener_thread.join(timeout=2.0)

    print("Void Launcher Shutdown Complete")
