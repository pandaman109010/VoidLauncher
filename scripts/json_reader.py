import json
import os
from pathlib import Path

#stores all the lists in ram
_config_cache = {}
# Track last modification time of config file
_config_mtime = 0

# Track active environments inside memery
_active_environments = set()

def load_config(force_reload=False): #reads config and chucks it in memy

    global _config_cache, _config_mtime

    # 1. finds the directory where we are chilling rn
    base_dir = Path(__file__).resolve().parent

    # 2. look for config chilling next to it
    config_path = base_dir / "config.json"

    # Check if we need to reload
    should_load = force_reload
    if not should_load and config_path.exists():
        try:
            current_mtime = os.path.getmtime(config_path)
            if current_mtime != _config_mtime:
                should_load = True
                _config_mtime = current_mtime
        except OSError:
            # If we can't get mtime, reload to be safe
            should_load = True

    if should_load:
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    _config_cache = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[ERROR] Could not load config.json: {e}")
                # Keep old config if new one is invalid
        else:
            print(f"[ERROR] Could not find config.json at: {config_path}")
            _config_cache = {}  # Clear cache if file doesn't exist

    return _config_cache

def get_global_setting(setting_name):
    #Call this to see global settings (e.g., get_global_setting('minimize-to-tray'))
    load_config()
    return _config_cache.get("global-settings", {}).get(setting_name, {}).get("enabled", False)

def get_all_personalities():
    #call to see all personalatys in config rn
    load_config()
    return _config_cache.get("personalities", [])

def get_personality_by_name(name):
    #get every setting in a spisifc personalaty
    load_config()
    for profile in get_all_personalities():
        if profile.get("name").lower() == name.lower():
            return profile
    return None

def set_personality_state(name, is_active):
    #sets if the personalaty is corrently running
    if is_active:
        _active_environments.add(name)
    else:
        _active_environments.discard(name)
        
def get_active_personalities():
    #shows what personalaty is running
    return list(_active_environments)

# loads into mem once imported
load_config()