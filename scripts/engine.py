import keyboard     #clicky wicky
import json_reader  # readey jsey
import app_handler  #opey clozey
import winreg       #starty warty
from pathlib import Path #findy pathy
import threading
import time
import os
import sys
import pystray
from PIL import Image, ImageDraw

# System tray icon setup
def create_image():
    """Create or load the system tray icon"""
    icon_path = Path(__file__).parent.parent / "UI" / "VL_logo.ico"
    if icon_path.exists():
        return Image.open(icon_path)
    else:
        # Create a simple fallback icon if VL_logo.ico is not found
        image = Image.new('RGB', (64, 64), color='black')
        dc = ImageDraw.Draw(image)
        dc.rectangle((16, 16, 48, 48), fill='white')
        return image

def open_settings(icon, item):
    """Open the settings application"""
    settings_path = Path(__file__).parent.parent / "UI" / "VoidLauncherUI.exe"
    if settings_path.exists():
        os.startfile(str(settings_path))
    else:
        print(f"Settings executable not found at: {settings_path}")

def show_console(icon, item):
    """Show or restore the console window"""
    # This will make the console visible if it was hidden
    # Since we're already in a console, this is more about bringing it to front
    # For now we'll just print a message
    print("Console is already visible")

def quit_application(icon, item):
    """Quit the entire application"""
    print("Shutting down Void Launcher...")
    icon.stop()  # Stop the system tray icon
    os._exit(0)  # Force exit the application

def setup_system_tray():
    """Set up the system tray icon and menu"""
    menu = pystray.Menu(
        pystray.MenuItem('Open Settings', open_settings),
        pystray.MenuItem('Show Console', show_console),
        pystray.MenuItem('Quit', quit_application)
    )

    image = create_image()
    icon = pystray.Icon("VoidLauncher", image, "Void Launcher", menu)
    return icon

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

def start_hotkey_listener():
    # Clear any existing hotkeys first
    keyboard.unhook_all()

    #findy personalaty
    profiles = json_reader.get_all_personalities()

    for profile in profiles: #runs throuh all personalatys
        # Safety check: skip if the user completely disabled this profile
        if not profile.get("enabled", False): #checks if they on
            continue

        shortcut = profile.get("trigger-shortcut", "")

        if shortcut:
            # Register the custom shortcut string dynamically
            keyboard.add_hotkey(shortcut, lambda p=profile: handle_shortcut_trigger(p))
            print(f"Registered shortkey: [{shortcut}] -> linked to '{profile['name']}'")

def config_watcher():
    """Monitors config file for changes and refreshes hotkeys when detected"""
    config_path = Path(__file__).parent / "config.json"
    last_mtime = 0

    # Get initial modification time
    if config_path.exists():
        try:
            last_mtime = os.path.getmtime(config_path)
        except OSError:
            pass

    while True:
        try:
            if config_path.exists():
                current_mtime = os.path.getmtime(config_path)
                if current_mtime != last_mtime:
                    print("Config file changed, refreshing hotkeys...")
                    start_hotkey_listener()
                    last_mtime = current_mtime
            else:
                # File was deleted, clear hotkeys
                if last_mtime != 0:
                    print("Config file deleted, clearing hotkeys...")
                    keyboard.unhook_all()
                    last_mtime = 0
        except OSError:
            # File might be temporarily inaccessible, continue monitoring
            pass

        # Check every 2 seconds (lightweight polling)
        time.sleep(2)

if __name__ == "__main__": #checky if mainy
    # starty warty
    if json_reader.get_global_setting("run-at-startup"):
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
    if not json_reader.get_global_setting("run-at-startup"): #not starty warty
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

    # Start the config file watcher in a background thread
    config_thread = threading.Thread(target=config_watcher, daemon=True)
    config_thread.start()

    # Set up system tray icon
    tray_icon = setup_system_tray()

    # Start the system tray icon in a background thread
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    # Initial hotkey setup
    start_hotkey_listener()
    print("Void Launcher Shortkey Engine is running")
    print("System tray icon is available - right-click for options")
    keyboard.wait()