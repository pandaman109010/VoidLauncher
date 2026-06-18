import keyboard     #clicky wicky
import json_reader  # readey jsey
import app_handler  #opey clozey 
import winreg       #starty warty
from pathlib import Path #findy pathy

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

    start_hotkey_listener()
    print("Void Launcher Shortkey Engine is running")
    keyboard.wait()