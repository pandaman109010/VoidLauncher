"""Handle Windows 11 system settings for Void Launcher personalities."""

import ctypes
import os
import subprocess
import time
import winreg

from pycaw.pycaw import AudioUtilities


# Stores the settings from before a personality changes them.
_original_settings = {}


# ============================================================
# WINDOWS HELPERS
# ============================================================

def _get_current_user_sid():
    """Get the SID of the current Windows user."""

    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"
            ],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        return output.strip()

    except Exception as error:
        print(
            f"[System Settings] Could not get user SID: {error}"
        )

        return None


def _broadcast_setting_change():
    """Tell Windows that a system setting changed."""

    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002

        user32 = ctypes.windll.user32

        result = ctypes.c_ulong()

        user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Windows",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result)
        )

    except Exception as error:
        print(
            f"[System Settings] Could not notify Windows: "
            f"{error}"
        )


# ============================================================
# VOLUME
# ============================================================

def get_volume():
    """Get the current Windows system volume."""

    try:
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume

        current_volume = round(
            volume.GetMasterVolumeLevelScalar() * 100
        )

        print(
            f"[System Settings] Current volume: "
            f"{current_volume}%."
        )

        return current_volume

    except Exception as error:
        print(
            f"[System Settings] Could not get volume: "
            f"{error}"
        )

        return None


def set_volume(volume_level):
    """Set the Windows system volume."""

    try:
        volume_level = max(
            0,
            min(100, int(volume_level))
        )

        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume

        volume.SetMasterVolumeLevelScalar(
            volume_level / 100,
            None
        )

        print(
            f"[System Settings] Volume set to "
            f"{volume_level}%."
        )

        return True

    except Exception as error:
        print(
            f"[System Settings] Could not set volume: "
            f"{error}"
        )

        return False


# ============================================================
# WINDOWS 11 DND / FOCUS ASSIST
# ============================================================

def _get_dnd_registry_value():
    """
    Read the Windows 11 Do Not Disturb CloudStore value.

    Windows 11 stores the real quiet-hours state inside
    CloudStore rather than the simple Notifications\\Settings
    registry value.
    """

    try:
        base_path = (
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\CloudStore\Store\Cache\DefaultAccount"
            r"\$$windows.data.notifications.quiethourssettings"
            r"\Current"
        )

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            base_path,
            0,
            winreg.KEY_READ
        )

        data = winreg.QueryValueEx(
            key,
            "Data"
        )[0]

        winreg.CloseKey(key)

        if not isinstance(data, bytes):
            return None

        return data

    except FileNotFoundError:
        print(
            "[System Settings] DND CloudStore key "
            "was not found."
        )

        return None

    except Exception as error:
        print(
            f"[System Settings] Could not read DND "
            f"CloudStore: {error}"
        )

        return None


def _dnd_data_is_enabled(data):
    """
    Determine whether the CloudStore DND data represents
    an active Priority Only / Do Not Disturb state.
    """

    if not data:
        return None

    try:
        # The CloudStore data contains the UTF-16LE profile
        # name near the end.
        text = data.decode(
            "utf-16-le",
            errors="ignore"
        )

        if "Microsoft.QuietHoursProfile.PriorityOnly" in text:
            return True

        if "Microsoft.QuietHoursProfile.Unrestricted" in text:
            return False

    except Exception:
        pass

    return None


def get_do_not_disturb():
    """Get the actual Windows 11 Do Not Disturb state."""

    data = _get_dnd_registry_value()

    if data is None:
        return None

    state = _dnd_data_is_enabled(data)

    if state is None:
        print(
            "[System Settings] Could not determine "
            "DND state from CloudStore."
        )

        return None

    print(
        f"[System Settings] Current DND: "
        f"{'ON' if state else 'OFF'}."
    )

    return state


def _find_quiet_hours_service():
    """
    Find the current user's Windows Push Notification
    User Service.

    Windows uses a per-user service such as:

        WpnUserService_12345
    """

    try:
        output = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-Service -Name 'WpnUserService*' "
                    "| Select-Object -ExpandProperty Name"
                )
            ],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        services = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        if services:
            return services[0]

    except Exception as error:
        print(
            f"[System Settings] Could not find "
            f"notification service: {error}"
        )

    return None


def _restart_notification_service():
    """
    Restart the user's notification service.

    This forces Windows to reload the CloudStore DND state.
    """

    service_name = _find_quiet_hours_service()

    if not service_name:
        print(
            "[System Settings] Could not find "
            "WpnUserService."
        )
        return False

    try:
        print(
            f"[System Settings] Restarting "
            f"{service_name}..."
        )

        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"Restart-Service -Name '{service_name}' "
                    f"-Force"
                )
            ],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        time.sleep(1)

        return True

    except Exception as error:
        print(
            f"[System Settings] Could not restart "
            f"notification service: {error}"
        )

        return False


def _create_dnd_data(enabled):
    """
    Create the CloudStore data used by Windows 11
    for Do Not Disturb.

    Windows stores the profile name as UTF-16LE.
    """

    if enabled:
        profile_name = (
            "Microsoft.QuietHoursProfile.PriorityOnly"
        )
    else:
        profile_name = (
            "Microsoft.QuietHoursProfile.Unrestricted"
        )

    # Windows stores the current UTC FILETIME in the
    # CloudStore data.
    filetime = ctypes.c_ulonglong()

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_uint32),
            ("dwHighDateTime", ctypes.c_uint32)
        ]

    current_filetime = FILETIME()

    ctypes.windll.kernel32.GetSystemTimeAsFileTime(
        ctypes.byref(current_filetime)
    )

    filetime_value = (
        current_filetime.dwLowDateTime
        | (
            current_filetime.dwHighDateTime
            << 32
        )
    )

    filetime_bytes = filetime_value.to_bytes(
        8,
        byteorder="little"
    )

    profile_bytes = profile_name.encode(
        "utf-16-le"
    )

    # CloudStore's binary structure used by the
    # Windows 11 quiet-hours setting.
    data = bytearray(
        [
            0x02,
            0x00,
            0x00,
            0x00
        ]
    )

    data.extend(filetime_bytes)

    data.extend(
        [
            0x00,
            0x00,
            0x00,
            0x00,
            0x43,
            0x42,
            0x01,
            0x00,
            0xC2,
            0x0A,
            0x01,
            0xD2,
            0x14,
            0x28
        ]
    )

    data.extend(
        [
            0x00,
            0xCA,
            0x28,
            0x00,
            0x00
        ]
    )

    data.extend(profile_bytes)

    return bytes(data)


def _set_dnd_cloudstore(enabled):
    """Write the actual Windows 11 DND CloudStore value."""

    try:
        path = (
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\CloudStore\Store\Cache\DefaultAccount"
            r"\$$windows.data.notifications.quiethourssettings"
            r"\Current"
        )

        data = _create_dnd_data(enabled)

        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            path
        )

        winreg.SetValueEx(
            key,
            "Data",
            0,
            winreg.REG_BINARY,
            data
        )

        winreg.CloseKey(key)

        print(
            "[System Settings] Updated Windows 11 "
            "DND CloudStore."
        )

        return True

    except Exception as error:
        print(
            f"[System Settings] Could not update "
            f"DND CloudStore: {error}"
        )

        return False


def set_do_not_disturb(enabled):
    """
    Set the actual Windows 11 Do Not Disturb state.
    """

    enabled = bool(enabled)

    print(
        f"[System Settings] Setting DND "
        f"to {'ON' if enabled else 'OFF'}..."
    )

    if not _set_dnd_cloudstore(enabled):
        return False

    _broadcast_setting_change()

    # Windows notification service caches this setting,
    # so restart it to make Windows reload the new value.
    _restart_notification_service()

    time.sleep(0.5)

    # Verify the actual stored state.
    actual_state = get_do_not_disturb()

    if actual_state == enabled:
        print(
            f"[System Settings] DND successfully changed "
            f"to {'ON' if enabled else 'OFF'}."
        )

        return True

    print(
        f"[System Settings] DND change could not be "
        f"verified. Actual state: {actual_state}"
    )

    return False


# ============================================================
# SAVE CURRENT SETTINGS
# ============================================================

def save_current_settings(profile_name):
    """Save the current Windows settings before changing them."""

    if profile_name in _original_settings:
        return

    current_volume = get_volume()
    current_dnd = get_do_not_disturb()

    _original_settings[profile_name] = {
        "volume": current_volume,
        "do-not-disturb": current_dnd
    }

    print(
        f"[System Settings] Saved settings for "
        f"'{profile_name}'."
    )

    if current_volume is not None:
        print(
            f"[System Settings] Original volume: "
            f"{current_volume}%."
        )

    if current_dnd is not None:
        print(
            f"[System Settings] Original DND: "
            f"{'ON' if current_dnd else 'OFF'}."
        )


# ============================================================
# APPLY PERSONALITY SETTINGS
# ============================================================

def apply_profile_settings(profile_data):
    """Save current settings and apply personality settings."""

    profile_name = profile_data.get("name")

    if not profile_name:
        return

    settings = profile_data.get(
        "system-settings-automation",
        {}
    )

    if not settings.get("enabled", False):
        return

    # Save the original settings BEFORE changing them.
    save_current_settings(profile_name)

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    volume_level = settings.get("volume-level")

    if volume_level is not None:
        set_volume(volume_level)

    # --------------------------------------------------------
    # Do Not Disturb
    # --------------------------------------------------------

    if "do-not-disturb" in settings:
        set_do_not_disturb(
            settings["do-not-disturb"]
        )


# ============================================================
# RESTORE PERSONALITY SETTINGS
# ============================================================

def restore_profile_settings(profile_name):
    """Restore the settings from before the personality activated."""

    if profile_name not in _original_settings:
        print(
            f"[System Settings] No saved settings "
            f"for '{profile_name}'."
        )

        return

    settings = _original_settings.pop(
        profile_name
    )

    # --------------------------------------------------------
    # Restore volume
    # --------------------------------------------------------

    if settings["volume"] is not None:
        set_volume(
            settings["volume"]
        )

    # --------------------------------------------------------
    # Restore DND
    # --------------------------------------------------------

    if settings["do-not-disturb"] is not None:
        set_do_not_disturb(
            settings["do-not-disturb"]
        )

    print(
        f"[System Settings] Restored settings "
        f"for '{profile_name}'."
    )