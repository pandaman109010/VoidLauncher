import json
from pathlib import Path
from threading import RLock


_config_cache = {}
_config_signature = None
_config_revision = 0
_config_lock = RLock()
_config_path = Path(__file__).resolve().parent / "config.json"

# Tracks profiles toggled during this engine session.
_active_environments = set()


def load_config():
    """Return cached config, reading config.json only after a successful change."""
    global _config_cache, _config_signature, _config_revision

    try:
        stat = _config_path.stat()
    except FileNotFoundError:
        print(f"[ERROR] Could not find config.json at: {_config_path}")
        return _config_cache

    signature = (stat.st_mtime_ns, stat.st_size)
    with _config_lock:
        if signature == _config_signature:
            return _config_cache

        try:
            with _config_path.open("r", encoding="utf-8") as config_file:
                updated_config = json.load(config_file)
        except (OSError, json.JSONDecodeError) as error:
            # Keep the last working config while the settings app is saving.
            print(f"[ERROR] Could not read config.json: {error}")
            return _config_cache

        _config_cache = updated_config
        _config_signature = signature
        _config_revision += 1
        return _config_cache


def get_config_revision():
    """Return a number that increases after each successful config reload."""
    load_config()
    with _config_lock:
        return _config_revision


def get_global_setting(setting_name):
    load_config()
    return _config_cache.get("global-settings", {}).get(setting_name, {}).get("enabled", False)


def get_all_personalities():
    load_config()
    return _config_cache.get("personalities", [])


def get_personality_by_name(name):
    load_config()
    for profile in _config_cache.get("personalities", []):
        if profile.get("name", "").casefold() == name.casefold():
            return profile
    return None


def get_enabled_profile_apps(name):
    """Return enabled app launch entries for a profile.

    Current settings use a comma-separated string. A JSON list is also
    accepted so the launcher can support richer entries later.
    """
    profile = get_personality_by_name(name)
    if profile is None:
        return []

    app_settings = profile.get("apps-to-launch", {})
    if not app_settings.get("enabled", False):
        return []

    paths = app_settings.get("paths", [])
    if isinstance(paths, str):
        return [path.strip() for path in paths.split(", ") if path.strip()]
    if isinstance(paths, list):
        return [path for path in paths if isinstance(path, (str, dict))]

    print(f"[ERROR] Invalid app paths for profile '{name}'.")
    return []


def set_personality_state(name, is_active):
    if is_active:
        _active_environments.add(name)
    else:
        _active_environments.discard(name)


def get_active_personalities():
    return list(_active_environments)


load_config()
