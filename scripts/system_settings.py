"""Handle Windows system settings for Void Launcher personalities."""

import ctypes
import os
import platform
import subprocess
import time
import winreg

from pycaw.pycaw import AudioUtilities


# Stores the settings from before a personality changes them.
_original_settings = {}


# ============================================================
# WINDOWS NOTIFICATION
# ============================================================

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

    Returns (registry_path, bytes) for the key that actually holds
    the live DND state on this build, or (None, None) if none does.
    The path is returned so writes land on the same key the OS
    reads from.
    """

    root = (
        r"Software\Microsoft\Windows\CurrentVersion"
        r"\CloudStore\Store\DefaultAccount\Current"
    )

    try:
        base_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            root,
            0,
            winreg.KEY_READ
        )
    except FileNotFoundError:
        print(
            "[System Settings] DND CloudStore root "
            "was not found."
        )
        return None, None

    try:
        index = 0

        while True:
            try:
                child = winreg.EnumKey(
                    base_key,
                    index
                )
                index += 1
            except OSError:
                break

            if (
                "donotdisturb.quiethourssettings"
                not in child
            ):
                continue

            parent = root + "\\" + child

            data = _read_dnd_data_at(
                parent
            )

            if data is not None:
                return parent, data

            try:
                sub_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    parent,
                    0,
                    winreg.KEY_READ
                )
            except OSError:
                continue

            try:
                sub_index = 0

                while True:
                    try:
                        sub_child = winreg.EnumKey(
                            sub_key,
                            sub_index
                        )
                        sub_index += 1
                    except OSError:
                        break

                    sub_path = (
                        parent
                        + "\\" + sub_child
                    )

                    data = (
                        _read_dnd_data_at(
                            sub_path
                        )
                    )

                    if data is not None:
                        return sub_path, data
            finally:
                winreg.CloseKey(sub_key)
    finally:
        winreg.CloseKey(base_key)

    print(
        "[System Settings] DND CloudStore key "
        "was not found."
    )

    return None, None


def _read_dnd_data_at(path):
    """Return the bytes of a key's Data value, or None."""

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            path,
            0,
            winreg.KEY_READ
        )
    except OSError:
        return None

    try:
        data = winreg.QueryValueEx(
            key,
            "Data"
        )[0]
    except OSError:
        return None
    finally:
        winreg.CloseKey(key)

    if isinstance(
        data,
        bytes
    ):
        return data

    return None


def _dnd_data_is_enabled(data):
    """Determine whether Windows DND is enabled."""

    if not data:
        return None

    on_marker = (
        "Microsoft.QuietHoursProfile.PriorityOnly"
    ).encode(
        "utf-16-le"
    )

    off_marker = (
        "Microsoft.QuietHoursProfile.Unrestricted"
    ).encode(
        "utf-16-le"
    )

    # Search the raw bytes: the blob header is 31 bytes (odd), so
    # decoding the whole blob from byte 0 shifts the marker out of
    # alignment on some builds.
    if on_marker in data:
        return True

    if off_marker in data:
        return False

    return None


def _is_windows_11():
    """Return True when running on Windows 11 or newer."""

    try:

        version = platform.version()

        numbers = [
            int(number)
            for number in version.split(".")
            if number.isdigit()
        ]

        if numbers:
            return numbers[-1] >= 22000

    except Exception:
        pass

    return False


def get_do_not_disturb():
    """Get the actual Do Not Disturb state."""

    if _is_windows_11():
        return _get_dnd_win11_state()

    return _get_dnd_win10_state()


def _get_dnd_win11_state():
    """Get the Windows 11 CloudStore Do Not Disturb state."""

    path, data = _get_dnd_registry_value()

    if data is None:
        return None

    print(
        f"[System Settings] DND registry key: "
        f"{path}"
    )

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


def _get_dnd_win10_state():
    """Get the Windows 10 Do Not Disturb state.

    The notification toast master switch is a DWORD under
    Notifications\\Settings. 0 silences toasts (Do Not Disturb),
    1 or absent allows them.
    """

    path = (
        r"Software\Microsoft\Windows\CurrentVersion"
        r"\Notifications\Settings"
    )

    try:

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            path,
            0,
            winreg.KEY_READ
        )

        try:

            toasts_enabled, _ = winreg.QueryValueEx(
                key,
                "NOC_GLOBAL_SETTING_TOASTS_ENABLED"
            )

        except FileNotFoundError:
            toasts_enabled = 1

        winreg.CloseKey(key)

    except OSError as error:
        print(
            f"[System Settings] Could not read "
            f"Windows 10 DND state: {error}"
        )
        return None

    state = (int(toasts_enabled) == 0)

    print(
        f"[System Settings] Current DND: "
        f"{'ON' if state else 'OFF'}."
    )

    return state


def _find_quiet_hours_service():
    """Find the current user's Windows notification service."""

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
    """Restart the user's notification service."""

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
    """Create Windows 11 CloudStore DND data.

    Fallback for when no live blob exists to patch. Mirrors the
    116-byte layout this Windows version actually writes (verified
    against test/dnd-dump.ps1).
    """

    if enabled:
        profile_name = (
            "Microsoft.QuietHoursProfile.PriorityOnly"
        )
    else:
        profile_name = (
            "Microsoft.QuietHoursProfile.Unrestricted"
        )

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

    data = bytearray(
        [
            0x43,
            0x42,
            0x01,
            0x00,
            0x0A,
            0x02,
            0x01,
            0x00,
            0x2A,
            0x06,
            0x00
        ]
    )

    data.extend(filetime_bytes)

    data.extend(
        [
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
        profile_name.encode(
            "utf-16-le"
        )
    )

    data.extend(
        [
            0xCA,
            0x28,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00
        ]
    )

    return bytes(data)


def _patch_dnd_data(
    data,
    enabled
):
    """Patch an existing CloudStore blob to the wanted DND state.

    The existing blob carries the OS session bytes and timestamps,
    so swapping only the profile string is accepted on far more
    Windows builds than rebuilding the value from scratch. The
    version byte at offset 10 is bumped by 2 like Windows does on
    every change, so the OS can notice the update even when the
    resulting state is unchanged.
    """

    if not isinstance(
        data,
        bytes
    ):
        return None

    wanted = (
        "Microsoft.QuietHoursProfile.PriorityOnly"
        if enabled
        else "Microsoft.QuietHoursProfile.Unrestricted"
    )

    current = (
        "Microsoft.QuietHoursProfile.PriorityOnly"
        if not enabled
        else "Microsoft.QuietHoursProfile.Unrestricted"
    )

    wanted_bytes = wanted.encode(
        "utf-16-le"
    )

    current_bytes = current.encode(
        "utf-16-le"
    )

    if len(wanted_bytes) != len(current_bytes):
        return None

    if wanted_bytes not in data:
        index = data.find(
            current_bytes
        )

        if index < 0:
            return None

        data = (
            data[:index]
            + wanted_bytes
            + data[index + len(current_bytes):]
        )

    # 116-byte 2024+ layout starts 43 42 01 00 0A 02; offset 10 is
    # a version counter the OS bumps by 2 per change. Bump it even
    # when the string was already the wanted one, so writing the
    # blob again forces the OS to reprocess it.
    if (
        len(data) >= 11
        and data[0:2] == b"\x43\x42"
    ):
        data = (
            data[:10]
            + bytes(
                [
                    (data[10] + 2) & 0xFF
                ]
            )
            + data[11:]
        )

    return data


def _set_dnd_cloudstore(enabled):
    """Write the Windows 11 DND CloudStore value.

    Writes back to the exact key the OS reads (the one found by
    _get_dnd_registry_value), preserving the blob's own session
    bytes. If it does not exist yet, the key is created under the
    default account's GUID with a freshly generated blob.
    """

    try:
        path, current_data = (
            _get_dnd_registry_value()
        )

        data = _patch_dnd_data(
            current_data,
            enabled
        )

        if data is None:

            data = (
                _create_dnd_data(
                    enabled
                )
            )

        if path is None:

            path = _build_default_dnd_path()

        if path is None:

            print(
                "[System Settings] Nothing to write: "
                "no DND CloudStore key exists."
            )

            return False

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
            f"[System Settings] Updated DND "
            f"CloudStore: {path}"
        )

        return True

    except Exception as error:
        print(
            f"[System Settings] DND update failed: "
            f"{error}"
        )

        return False


def _build_default_dnd_path():
    """Build the DND CloudStore path for this default account.

    Reuses the GUID from any existing donotdisturb sibling key so
    the created key lives under the same account GUID, falling back
    to the well-known default account GUID.
    """

    root = (
        r"Software\Microsoft\Windows\CurrentVersion"
        r"\CloudStore\Store\DefaultAccount\Current"
    )

    account_guid = (
        r"{97c6ee2c-3831-4880-9c15-e7de7ca182a2}"
    )

    try:
        base_key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            root,
            0,
            winreg.KEY_READ
        )
    except FileNotFoundError:
        return None

    try:
        index = 0

        while True:
            try:
                child = winreg.EnumKey(
                    base_key,
                    index
                )
                index += 1
            except OSError:
                break

            if (
                "$windows.data.donotdisturb" in child
                and child.startswith("{")
            ):
                account_guid = (
                    child[:child.index("$")]
                )
                break
    finally:
        winreg.CloseKey(base_key)

    return (
        root
        + "\\" + account_guid
        + "$windows.data.donotdisturb.quiethourssettings"
        + "\\windows.data.donotdisturb.quiethourssettings"
    )


def _set_dnd_win10(enabled):
    """Set the Windows 10 Do Not Disturb state."""

    path = (
        r"Software\Microsoft\Windows\CurrentVersion"
        r"\Notifications\Settings"
    )

    toasts_enabled = 0 if enabled else 1

    try:

        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            path
        )

        winreg.SetValueEx(
            key,
            "NOC_GLOBAL_SETTING_TOASTS_ENABLED",
            0,
            winreg.REG_DWORD,
            toasts_enabled
        )

        winreg.CloseKey(key)

        print(
            f"[System Settings] Windows 10 DND set to "
            f"{'ON' if enabled else 'OFF'} "
            f"(NOC_GLOBAL_SETTING_TOASTS_ENABLED="
            f"{toasts_enabled})."
        )

        return True

    except Exception as error:

        print(
            f"[System Settings] Could not set "
            f"Windows 10 DND: {error}"
        )

        return False


def set_do_not_disturb(enabled):
    """Set the actual Do Not Disturb state."""

    enabled = bool(enabled)

    print(
        f"[System Settings] Setting DND "
        f"to {'ON' if enabled else 'OFF'}..."
    )

    if _is_windows_11():
        ok = _set_dnd_cloudstore(enabled)
    else:
        ok = _set_dnd_win10(enabled)

    if not ok:
        return False

    _broadcast_setting_change()

    _restart_notification_service()

    time.sleep(0.5)

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
# WALLPAPER
# ============================================================

def get_wallpaper():
    """Get the current Windows desktop wallpaper path."""

    try:
        SPI_GETDESKWALLPAPER = 0x0073

        wallpaper_buffer = ctypes.create_unicode_buffer(260)

        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER,
            260,
            wallpaper_buffer,
            0
        )

        if not result:
            print(
                "[System Settings] Could not get "
                "current wallpaper."
            )
            return None

        wallpaper = wallpaper_buffer.value

        if not wallpaper:
            print(
                "[System Settings] Current wallpaper "
                "path is empty."
            )
            return None

        print(
            f"[System Settings] Current wallpaper: "
            f"{wallpaper}"
        )

        return wallpaper

    except Exception as error:
        print(
            f"[System Settings] Could not get wallpaper: "
            f"{error}"
        )

        return None


def set_wallpaper(wallpaper_path):
    """Change the Windows desktop wallpaper."""

    try:
        if not wallpaper_path:
            print(
                "[System Settings] No wallpaper path "
                "was provided."
            )
            return False

        wallpaper_path = os.path.expandvars(
            os.path.expanduser(
                str(wallpaper_path)
            )
        )

        if not os.path.isfile(wallpaper_path):
            print(
                f"[System Settings] Wallpaper not found: "
                f"{wallpaper_path}"
            )
            return False

        SPI_SETDESKWALLPAPER = 0x0014
        SPIF_UPDATEINIFILE = 0x01
        SPIF_SENDCHANGE = 0x02

        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            wallpaper_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        )

        if not result:
            print(
                f"[System Settings] Could not set wallpaper: "
                f"{wallpaper_path}"
            )
            return False

        print(
            f"[System Settings] Wallpaper changed to: "
            f"{wallpaper_path}"
        )

        return True

    except Exception as error:
        print(
            f"[System Settings] Could not set wallpaper: "
            f"{error}"
        )

        return False


def save_current_wallpaper(profile_name):
    """Save the wallpaper before changing it."""

    if profile_name not in _original_settings:
        _original_settings[profile_name] = {}

    if "wallpaper" in _original_settings[profile_name]:
        return

    current_wallpaper = get_wallpaper()

    _original_settings[profile_name]["wallpaper"] = (
        current_wallpaper
    )

    if current_wallpaper:
        print(
            f"[System Settings] Saved original wallpaper "
            f"for '{profile_name}'."
        )


# ============================================================
# SAVE CURRENT SETTINGS
# ============================================================

def save_current_settings(profile_name):
    """Save the current Windows settings before changing them."""

    if profile_name not in _original_settings:
        _original_settings[profile_name] = {}

    current_volume = get_volume()
    current_dnd = get_do_not_disturb()

    _original_settings[profile_name]["volume"] = current_volume
    _original_settings[profile_name]["do-not-disturb"] = current_dnd

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

    wallpaper_settings = profile_data.get(
        "wallpaper-switch",
        {}
    )

    # --------------------------------------------------------
    # Save settings
    # --------------------------------------------------------

    if settings.get("enabled", False):
        save_current_settings(profile_name)

    if wallpaper_settings.get("enabled", False):
        save_current_wallpaper(profile_name)

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    if settings.get("enabled", False):

        volume_level = settings.get(
            "volume-level"
        )

        if volume_level is not None:
            set_volume(volume_level)

        # ----------------------------------------------------
        # Do Not Disturb
        # ----------------------------------------------------

        if "do-not-disturb" in settings:
            set_do_not_disturb(
                settings["do-not-disturb"]
            )

    # --------------------------------------------------------
    # Wallpaper
    # --------------------------------------------------------

    if wallpaper_settings.get("enabled", False):

        wallpaper_path = wallpaper_settings.get(
            "wallpaper-path",
            ""
        )

        if wallpaper_path:
            set_wallpaper(wallpaper_path)


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

    if settings.get("volume") is not None:
        set_volume(
            settings["volume"]
        )

    # --------------------------------------------------------
    # Restore DND
    # --------------------------------------------------------

    if settings.get("do-not-disturb") is not None:
        set_do_not_disturb(
            settings["do-not-disturb"]
        )

    # --------------------------------------------------------
    # Restore wallpaper
    # --------------------------------------------------------

    if settings.get("wallpaper"):
        set_wallpaper(
            settings["wallpaper"]
        )

    print(
        f"[System Settings] Restored settings "
        f"for '{profile_name}'."
    )