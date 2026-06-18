
def launch_profile_environment(profile_data):
    import json_reader
    json_reader.load_config()
    current_profile = json_reader.get_personality_by_name(profile_data["name"]) or profile_data
    print(f"\n[App Handler] Activating environment: {profile_data['name']}")
    active_list = json_reader.get_active_personalities()
    print(f" -> Active list called inside app_handler: {active_list}")
    print(f"opend {active_list}")
    print(f"opening {current_profile['apps-to-launch']['paths']}")
    #put app open code here later

def close_profile_environment(profile_data):
    import json_reader
    """Handles closing apps when the shortcut is hit again."""
    json_reader.load_config()
    current_profile = json_reader.get_personality_by_name(profile_data["name"]) or profile_data
    print(f"\n[App Handler] Deactivating environment: {profile_data['name']}")
    print(f"just closed personalaty {current_profile['name']}")
    print(f"along with {current_profile['apps-to-launch']['paths']}")
    # put app close here later
    