"""Handle Windows virtual desktops for Void Launcher.

Supports:
    - Windows 10 2004+
    - Windows 11
    - Real Windows virtual desktop names
    - Desktop creation
    - Desktop switching
    - Desktop deletion
    - Multiple active personalities
    - Safe tracking using desktop GUIDs

pyvda is still used for the actual desktop operations.
Windows Registry is used for the desktop names because pyvda
does not expose desktop naming in all versions.
"""

import ctypes
import os
import platform
import re
import winreg

from pyvda import VirtualDesktop, get_virtual_desktops


# ============================================================
# STATE
# ============================================================

# The desktop the user was on before activating each personality.
#
# {
#     "Gaming": <desktop identity>,
#     "Focus Mode": <desktop identity>
# }
#
_previous_desktops = {}


# The desktop assigned to each active personality.
#
# {
#     "Gaming": {
#         "desktop": <VirtualDesktop>,
#         "guid": "...",
#         "created": True,
#         "target_name": "Gaming"
#     }
# }
#
_profile_desktops = {}


# ============================================================
# WINDOWS VERSION
# ============================================================

def _get_windows_build():
    """Return the Windows build number."""

    try:

        version = platform.version()

        numbers = re.findall(
            r"\d+",
            version
        )

        if numbers:

            return int(
                numbers[-1]
            )

    except Exception:
        pass

    return 0


# ============================================================
# DESKTOP NUMBERS
# ============================================================

def _get_desktop_number(desktop):
    """Safely get a virtual desktop number."""

    if desktop is None:
        return None

    try:

        number = getattr(
            desktop,
            "number",
            None
        )

        if callable(number):
            number = number()

        if number is None:
            return None

        return int(number)

    except Exception:
        return None


# ============================================================
# DESKTOP GUID
# ============================================================

def _get_desktop_guid(desktop):
    """
    Get the real Windows GUID for a virtual desktop.

    pyvda does not expose this directly as a normal public
    property, so several compatible methods are attempted.
    """

    if desktop is None:
        return None

    # --------------------------------------------------------
    # Some versions expose an id property.
    # --------------------------------------------------------

    possible_attributes = (
        "id",
        "guid",
        "desktop_id",
        "desktop_guid"
    )

    for attribute_name in possible_attributes:

        try:

            value = getattr(
                desktop,
                attribute_name,
                None
            )

            if callable(value):
                value = value()

            if value is None:
                continue

            guid = _normalise_guid(
                value
            )

            if guid is not None:
                return guid

        except Exception:
            pass

    # --------------------------------------------------------
    # Newer/internal pyvda implementations may expose the
    # underlying COM object.
    # --------------------------------------------------------

    possible_objects = (
        "_desktop",
        "_virtual_desktop",
        "_ivd",
        "ivd",
        "_obj"
    )

    for object_name in possible_objects:

        try:

            underlying = getattr(
                desktop,
                object_name,
                None
            )

            if underlying is None:
                continue

            get_id = getattr(
                underlying,
                "GetId",
                None
            )

            if callable(get_id):

                value = get_id()

                guid = _normalise_guid(
                    value
                )

                if guid is not None:
                    return guid

        except Exception:
            pass

    # --------------------------------------------------------
    # Last resort:
    #
    # Windows stores the virtual desktop IDs in:
    #
    # HKCU\...\Explorer\VirtualDesktops\VirtualDesktopIDs
    #
    # We match the desktop's position.
    # --------------------------------------------------------

    number = _get_desktop_number(
        desktop
    )

    if number is not None:

        return _get_guid_from_registry_index(
            number
        )

    return None


def _normalise_guid(value):
    """Convert a GUID-like value into a standard string."""

    if value is None:
        return None

    try:

        if isinstance(
            value,
            bytes
        ):

            if len(value) == 16:

                import uuid

                return str(
                    uuid.UUID(
                        bytes_le=value
                    )
                ).lower()

        text = str(
            value
        ).strip()

        if not text:
            return None

        text = text.strip(
            "{}"
        )

        import uuid

        parsed = uuid.UUID(
            text
        )

        return str(
            parsed
        ).lower()

    except Exception:
        return None


def _get_all_registry_desktop_guids():
    """
    Read Windows' actual virtual desktop GUID list.

    Windows stores the IDs in the VirtualDesktopIDs binary
    registry value, 16 bytes per GUID.
    """

    path = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion"
        r"\Explorer\VirtualDesktops"
    )

    try:

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            path,
            0,
            winreg.KEY_READ
        )

        data = winreg.QueryValueEx(
            key,
            "VirtualDesktopIDs"
        )[0]

        winreg.CloseKey(
            key
        )

        if not isinstance(
            data,
            bytes
        ):

            return []

        import uuid

        guids = []

        for position in range(
            0,
            len(data),
            16
        ):

            chunk = data[
                position:position + 16
            ]

            if len(chunk) != 16:
                continue

            try:

                guid = str(
                    uuid.UUID(
                        bytes_le=chunk
                    )
                ).lower()

                guids.append(
                    guid
                )

            except Exception:
                pass

        return guids

    except Exception:
        return []


def _get_guid_from_registry_index(
    index
):
    """Get a desktop GUID using its current Windows index."""

    guids = (
        _get_all_registry_desktop_guids()
    )

    if (
        index < 0
        or index >= len(guids)
    ):

        return None

    return guids[
        index
    ]


# ============================================================
# DESKTOP NAME
# ============================================================

def _get_desktop_name_from_guid(
    desktop_guid
):
    """Read the real Windows desktop name from Explorer."""

    if not desktop_guid:
        return ""

    desktop_guid = str(
        desktop_guid
    ).strip(
        "{}"
    ).lower()

    base_path = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion"
        r"\Explorer\VirtualDesktops\Desktops"
    )

    # --------------------------------------------------------
    # Normal Windows location.
    # --------------------------------------------------------

    desktop_path = (
        base_path
        + "\\{"
        + desktop_guid
        + "}"
    )

    try:

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            desktop_path,
            0,
            winreg.KEY_READ
        )

        value = winreg.QueryValueEx(
            key,
            "Name"
        )[0]

        winreg.CloseKey(
            key
        )

        if value:
            return str(
                value
            )

    except Exception:
        pass

    # --------------------------------------------------------
    # Windows can also have session-specific desktop data.
    # --------------------------------------------------------

    try:

        session_id = (
            ctypes.windll.kernel32
            .ProcessIdToSessionId
        )

        current_pid = (
            ctypes.windll.kernel32
            .GetCurrentProcessId()
        )

        session = ctypes.c_uint32()

        if session_id(
            current_pid,
            ctypes.byref(
                session
            )
        ):

            session_path = (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion"
                r"\Explorer\SessionInfo\\"
                + str(
                    session.value
                )
                + r"\VirtualDesktops\Desktops\{"
                + desktop_guid
                + "}"
            )

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                session_path,
                0,
                winreg.KEY_READ
            )

            value = winreg.QueryValueEx(
                key,
                "Name"
            )[0]

            winreg.CloseKey(
                key
            )

            if value:
                return str(
                    value
                )

    except Exception:
        pass

    return ""


def _get_desktop_name(
    desktop
):
    """Get the actual Windows desktop name."""

    guid = _get_desktop_guid(
        desktop
    )

    if guid:

        name = (
            _get_desktop_name_from_guid(
                guid
            )
        )

        if name:
            return name

    number = _get_desktop_number(
        desktop
    )

    if number is not None:

        return (
            f"Desktop {number + 1}"
        )

    return ""


def _set_desktop_name(
    desktop,
    desktop_name
):
    """
    Give a Windows virtual desktop its real name.

    Windows 10 2004+ supports desktop names. The name is stored
    by Explorer against the desktop GUID.
    """

    if desktop is None:
        return False

    desktop_name = str(
        desktop_name
    ).strip()

    if not desktop_name:
        return False

    guid = _get_desktop_guid(
        desktop
    )

    if not guid:

        print(
            "[Virtual Desktop] Could not determine "
            "the Windows GUID for the desktop."
        )

        return False

    # --------------------------------------------------------
    # Write the name to the Explorer desktop registry key.
    # --------------------------------------------------------

    path = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion"
        r"\Explorer\VirtualDesktops\Desktops\{"
        + guid
        + "}"
    )

    try:

        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            path
        )

        winreg.SetValueEx(
            key,
            "Name",
            0,
            winreg.REG_SZ,
            desktop_name
        )

        winreg.CloseKey(
            key
        )

        print(
            f"[Virtual Desktop] Named desktop "
            f"'{desktop_name}'."
        )

        # ----------------------------------------------------
        # Tell Explorer that its settings changed.
        # ----------------------------------------------------

        try:

            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A

            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "VirtualDesktops",
                0x0002,
                2000,
                None
            )

        except Exception:
            pass

        return True

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not name desktop "
            f"'{desktop_name}': {error}"
        )

        return False


# ============================================================
# DESKTOP IDENTITY
# ============================================================

def _desktop_identity(
    desktop
):
    """
    Return a stable identity for a desktop.

    GUID is preferred because desktop numbers change when
    desktops are removed.
    """

    if desktop is None:
        return None

    guid = _get_desktop_guid(
        desktop
    )

    if guid:

        return (
            "guid",
            guid
        )

    number = _get_desktop_number(
        desktop
    )

    if number is not None:

        return (
            "number",
            number
        )

    return None


def _same_desktop(
    first,
    second
):
    """Determine whether two desktop objects represent the same desktop."""

    first_identity = _desktop_identity(
        first
    )

    second_identity = _desktop_identity(
        second
    )

    if (
        first_identity is None
        or second_identity is None
    ):

        return False

    return (
        first_identity
        == second_identity
    )


# ============================================================
# DESKTOP EXISTENCE / REFRESH
# ============================================================

def _desktop_exists(
    desktop
):
    """Check whether a desktop still exists."""

    if desktop is None:
        return False

    wanted_guid = _get_desktop_guid(
        desktop
    )

    if wanted_guid:

        for existing in get_all_desktops():

            existing_guid = (
                _get_desktop_guid(
                    existing
                )
            )

            if (
                existing_guid
                == wanted_guid
            ):

                return True

    # Fallback to object equality/number.
    for existing in get_all_desktops():

        if _same_desktop(
            existing,
            desktop
        ):

            return True

    return False


def _get_fresh_desktop(
    desktop
):
    """
    Get a fresh pyvda object representing the same desktop.

    GUID matching is used first so deleting another desktop
    cannot accidentally redirect the reference.
    """

    if desktop is None:
        return None

    wanted_guid = _get_desktop_guid(
        desktop
    )

    desktops = get_all_desktops()

    # --------------------------------------------------------
    # Best method: GUID.
    # --------------------------------------------------------

    if wanted_guid:

        for existing in desktops:

            existing_guid = (
                _get_desktop_guid(
                    existing
                )
            )

            if (
                existing_guid
                == wanted_guid
            ):

                return existing

    # --------------------------------------------------------
    # Fallback: desktop number.
    # --------------------------------------------------------

    wanted_number = _get_desktop_number(
        desktop
    )

    if wanted_number is not None:

        for existing in desktops:

            if (
                _get_desktop_number(
                    existing
                )
                == wanted_number
            ):

                return existing

    return None


# ============================================================
# DESKTOP GETTERS
# ============================================================

def get_current_desktop():
    """Return the currently active virtual desktop."""

    try:

        return VirtualDesktop.current()

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not get current "
            f"desktop: {error}"
        )

        return None


def get_all_desktops():
    """Return all current virtual desktops."""

    try:

        return list(
            get_virtual_desktops()
        )

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not get desktop list: "
            f"{error}"
        )

        return []


# ============================================================
# DESKTOP DESCRIPTION
# ============================================================

def _describe_desktop(
    desktop
):
    """Return a useful desktop description."""

    if desktop is None:
        return "unknown desktop"

    name = _get_desktop_name(
        desktop
    )

    number = _get_desktop_number(
        desktop
    )

    if name:

        if number is not None:

            return (
                f"'{name}' "
                f"(Desktop {number + 1})"
            )

        return f"'{name}'"

    if number is not None:

        return (
            f"Desktop {number + 1}"
        )

    return "unknown desktop"


# ============================================================
# DESKTOP CREATION
# ============================================================

def _create_desktop():
    """Create a new virtual desktop."""

    try:

        desktop = (
            VirtualDesktop.create()
        )

        print(
            "[Virtual Desktop] Created a new "
            "virtual desktop."
        )

        # ----------------------------------------------------
        # Refresh it immediately because Windows may have
        # changed the desktop list.
        # ----------------------------------------------------

        fresh_desktop = (
            _get_fresh_desktop(
                desktop
            )
        )

        if fresh_desktop is not None:

            desktop = fresh_desktop

        return desktop

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not create desktop: "
            f"{error}"
        )

        return None


# ============================================================
# DESKTOP SWITCHING
# ============================================================

def switch_to_desktop(
    desktop
):
    """Switch Windows to a specific virtual desktop."""

    if desktop is None:
        return False

    fresh_desktop = (
        _get_fresh_desktop(
            desktop
        )
    )

    if fresh_desktop is None:

        print(
            "[Virtual Desktop] Could not switch because "
            "the desktop no longer exists."
        )

        return False

    try:

        fresh_desktop.go()

        print(
            f"[Virtual Desktop] Switched to "
            f"{_describe_desktop(fresh_desktop)}."
        )

        return True

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not switch desktop: "
            f"{error}"
        )

        return False


# ============================================================
# FIND DESKTOP BY NAME
# ============================================================

def find_desktop_by_name(
    desktop_name
):
    """Find a real Windows virtual desktop by its name."""

    if not desktop_name:
        return None

    wanted_name = str(
        desktop_name
    ).strip().casefold()

    for desktop in get_all_desktops():

        current_name = (
            _get_desktop_name(
                desktop
            )
        )

        if (
            current_name
            and current_name.casefold()
            == wanted_name
        ):

            return desktop

    return None


# ============================================================
# PERSONALITY DESKTOPS
# ============================================================

def switch_to_profile_desktop(
    profile_data
):
    """
    Switch to the desktop for a personality.

    A new desktop is created for the personality and receives
    its configured Windows desktop name.

    Example:

        target-desktop-name = "Gaming"

    results in an actual Windows desktop named:

        Gaming
    """

    profile_name = profile_data.get(
        "name"
    )

    if not profile_name:

        print(
            "[Virtual Desktop] Profile has no name."
        )

        return False

    settings = profile_data.get(
        "virtual-desktop-switch",
        {}
    )

    if not settings.get(
        "enabled",
        False
    ):

        print(
            f"[Virtual Desktop] Virtual desktop switching "
            f"is disabled for '{profile_name}'."
        )

        return False

    target_name = str(
        settings.get(
            "target-desktop-name",
            ""
        )
    ).strip()

    if not target_name:

        target_name = profile_name

    # --------------------------------------------------------
    # If this personality already has a desktop, return to it.
    # --------------------------------------------------------

    existing_info = (
        _profile_desktops.get(
            profile_name
        )
    )

    if existing_info is not None:

        existing_desktop = (
            existing_info.get(
                "desktop"
            )
        )

        fresh_existing = (
            _get_fresh_desktop(
                existing_desktop
            )
        )

        if fresh_existing is not None:

            existing_info[
                "desktop"
            ] = fresh_existing

            # Re-apply the name in case Explorer changed it.
            _set_desktop_name(
                fresh_existing,
                existing_info.get(
                    "target_name",
                    target_name
                )
            )

            print(
                f"[Virtual Desktop] Returning to "
                f"'{profile_name}' desktop: "
                f"{_describe_desktop(fresh_existing)}."
            )

            return switch_to_desktop(
                fresh_existing
            )

        _profile_desktops.pop(
            profile_name,
            None
        )

        print(
            f"[Virtual Desktop] Stored desktop for "
            f"'{profile_name}' no longer exists."
        )

    # --------------------------------------------------------
    # Save the desktop the user was on.
    # --------------------------------------------------------

    if profile_name not in _previous_desktops:

        current_desktop = (
            get_current_desktop()
        )

        if current_desktop is not None:

            _previous_desktops[
                profile_name
            ] = {
                "desktop": current_desktop,
                "identity": _desktop_identity(
                    current_desktop
                )
            }

            print(
                f"[Virtual Desktop] Saved previous desktop "
                f"for '{profile_name}': "
                f"{_describe_desktop(current_desktop)}."
            )

    # --------------------------------------------------------
    # Create a new desktop.
    # --------------------------------------------------------

    print(
        f"[Virtual Desktop] Creating desktop for "
        f"'{profile_name}'..."
    )

    new_desktop = (
        _create_desktop()
    )

    if new_desktop is None:
        return False

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Name the actual Windows desktop.
    # --------------------------------------------------------

    named = _set_desktop_name(
        new_desktop,
        target_name
    )

    if not named:

        print(
            f"[Virtual Desktop] WARNING: Could not set "
            f"Windows desktop name to '{target_name}'."
        )

    # --------------------------------------------------------
    # Refresh after naming.
    # --------------------------------------------------------

    fresh_new_desktop = (
        _get_fresh_desktop(
            new_desktop
        )
    )

    if fresh_new_desktop is not None:

        new_desktop = (
            fresh_new_desktop
        )

    desktop_guid = (
        _get_desktop_guid(
            new_desktop
        )
    )

    _profile_desktops[
        profile_name
    ] = {
        "desktop": new_desktop,
        "guid": desktop_guid,
        "created": True,
        "target_name": target_name
    }

    print(
        f"[Virtual Desktop] Desktop "
        f"'{target_name}' belongs to "
        f"'{profile_name}'."
    )

    if desktop_guid:

        print(
            f"[Virtual Desktop] Desktop GUID: "
            f"{desktop_guid}"
        )

    return switch_to_desktop(
        new_desktop
    )


# ============================================================
# UPDATE REFERENCES BEFORE DELETION
# ============================================================

def _update_references_before_deleting(
    deleted_desktop,
    replacement_desktop
):
    """
    Update saved previous-desktop references before deleting
    a desktop.

    This specifically fixes:

        Desktop 1
            |
        Gaming -> Desktop 2
            |
        Focus -> Desktop 3

    When Gaming closes and Desktop 2 is deleted, Focus must
    not continue holding a reference to the deleted Desktop 2.
    """

    deleted_guid = (
        _get_desktop_guid(
            deleted_desktop
        )
    )

    replacement_fresh = (
        _get_fresh_desktop(
            replacement_desktop
        )
    )

    if replacement_fresh is None:
        return

    replacement_guid = (
        _get_desktop_guid(
            replacement_fresh
        )
    )

    for profile_name, info in list(
        _previous_desktops.items()
    ):

        previous_desktop = (
            info.get(
                "desktop"
            )
            if isinstance(
                info,
                dict
            )
            else info
        )

        previous_guid = (
            _get_desktop_guid(
                previous_desktop
            )
        )

        # GUID comparison is safest.
        if (
            deleted_guid
            and previous_guid
            and deleted_guid == previous_guid
        ):

            _previous_desktops[
                profile_name
            ] = {
                "desktop": replacement_fresh,
                "identity": (
                    "guid",
                    replacement_guid
                )
                if replacement_guid
                else _desktop_identity(
                    replacement_fresh
                )
            }

            print(
                f"[Virtual Desktop] Updated previous "
                f"desktop for '{profile_name}' to "
                f"{_describe_desktop(replacement_fresh)} "
                f"because its previous desktop was deleted."
            )

            continue

        # Fallback if GUID isn't available.
        if _same_desktop(
            previous_desktop,
            deleted_desktop
        ):

            _previous_desktops[
                profile_name
            ] = {
                "desktop": replacement_fresh,
                "identity": _desktop_identity(
                    replacement_fresh
                )
            }

            print(
                f"[Virtual Desktop] Updated previous "
                f"desktop for '{profile_name}' to "
                f"{_describe_desktop(replacement_fresh)}."
            )


# ============================================================
# DESKTOP DELETION
# ============================================================

def _delete_desktop(
    desktop,
    fallback_desktop
):
    """Delete a virtual desktop safely."""

    if desktop is None:
        return False

    fresh_desktop = (
        _get_fresh_desktop(
            desktop
        )
    )

    fresh_fallback = (
        _get_fresh_desktop(
            fallback_desktop
        )
    )

    if fresh_desktop is None:

        print(
            "[Virtual Desktop] Desktop was already deleted."
        )

        return True

    if fresh_fallback is None:

        print(
            "[Virtual Desktop] Cannot delete desktop "
            "because the fallback desktop does not exist."
        )

        return False

    if _same_desktop(
        fresh_desktop,
        fresh_fallback
    ):

        print(
            "[Virtual Desktop] Refusing to delete a desktop "
            "using itself as the fallback."
        )

        return False

    # --------------------------------------------------------
    # Update other personalities before deletion.
    # --------------------------------------------------------

    _update_references_before_deleting(
        fresh_desktop,
        fresh_fallback
    )

    desktop_name = (
        _get_desktop_name(
            fresh_desktop
        )
    )

    desktop_guid = (
        _get_desktop_guid(
            fresh_desktop
        )
    )

    try:

        print(
            f"[Virtual Desktop] Deleting "
            f"{_describe_desktop(fresh_desktop)}."
        )

        fresh_desktop.remove(
            fresh_fallback
        )

        print(
            f"[Virtual Desktop] Deleted "
            f"'{desktop_name or 'desktop'}'."
        )

        # ----------------------------------------------------
        # Remove its Explorer name entry.
        #
        # Windows normally cleans this up itself, but removing
        # it here prevents stale names if Windows leaves the
        # registry entry behind.
        # ----------------------------------------------------

        if desktop_guid:

            try:

                path = (
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
                    r"\Explorer\VirtualDesktops\Desktops\{"
                    + desktop_guid
                    + "}"
                )

                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    path
                )

            except Exception:
                pass

        return True

    except Exception as error:

        print(
            f"[Virtual Desktop] Could not delete desktop: "
            f"{error}"
        )

        return False


# ============================================================
# RESTORE PREVIOUS DESKTOP
# ============================================================

def restore_previous_desktop(
    profile_name
):
    """
    Return to the desktop that was active before the
    personality was opened.

    Only desktops created by Void Launcher are deleted.
    """

    previous_info = (
        _previous_desktops.pop(
            profile_name,
            None
        )
    )

    profile_info = (
        _profile_desktops.pop(
            profile_name,
            None
        )
    )

    personality_desktop = None
    was_created = False

    if profile_info is not None:

        personality_desktop = (
            profile_info.get(
                "desktop"
            )
        )

        was_created = bool(
            profile_info.get(
                "created",
                False
            )
        )

    # --------------------------------------------------------
    # Extract saved previous desktop.
    # --------------------------------------------------------

    if isinstance(
        previous_info,
        dict
    ):

        previous_desktop = (
            previous_info.get(
                "desktop"
            )
        )

    else:

        previous_desktop = (
            previous_info
        )

    # --------------------------------------------------------
    # Refresh the actual desktop objects.
    # --------------------------------------------------------

    fresh_previous = (
        _get_fresh_desktop(
            previous_desktop
        )
    )

    fresh_personality = (
        _get_fresh_desktop(
            personality_desktop
        )
    )

    # --------------------------------------------------------
    # If the previous desktop disappeared, select a safe
    # desktop that isn't the personality desktop.
    # --------------------------------------------------------

    if fresh_previous is None:

        all_desktops = (
            get_all_desktops()
        )

        for desktop in all_desktops:

            if (
                fresh_personality is not None
                and _same_desktop(
                    desktop,
                    fresh_personality
                )
            ):

                continue

            fresh_previous = desktop

            break

    # --------------------------------------------------------
    # Switch away from the personality desktop.
    # --------------------------------------------------------

    switched = False

    if fresh_previous is not None:

        print(
            f"[Virtual Desktop] Returning to "
            f"{_describe_desktop(fresh_previous)} "
            f"for '{profile_name}'."
        )

        switched = switch_to_desktop(
            fresh_previous
        )

    else:

        print(
            f"[Virtual Desktop] No valid previous desktop "
            f"was available for '{profile_name}'."
        )

    # --------------------------------------------------------
    # Delete only a desktop created by Void Launcher.
    # --------------------------------------------------------

    if (
        was_created
        and fresh_personality is not None
    ):

        current_desktop = (
            get_current_desktop()
        )

        # Never delete the desktop we're currently using.
        if (
            current_desktop is not None
            and _same_desktop(
                current_desktop,
                fresh_personality
            )
        ):

            print(
                "[Virtual Desktop] Still on the personality "
                "desktop. It will not be deleted."
            )

        elif fresh_previous is not None:

            _delete_desktop(
                fresh_personality,
                fresh_previous
            )

    return switched


# ============================================================
# PROFILE DESKTOP ACCESS
# ============================================================

def get_profile_desktop(
    profile_name
):
    """Return the current desktop assigned to a profile."""

    profile_info = (
        _profile_desktops.get(
            profile_name
        )
    )

    if profile_info is None:
        return None

    desktop = (
        profile_info.get(
            "desktop"
        )
    )

    fresh_desktop = (
        _get_fresh_desktop(
            desktop
        )
    )

    if fresh_desktop is not None:

        profile_info[
            "desktop"
        ] = fresh_desktop

    return fresh_desktop


# ============================================================
# DEBUGGING
# ============================================================

def print_desktop_list():
    """Print all current desktops with their real Windows names."""

    desktops = (
        get_all_desktops()
    )

    if not desktops:

        print(
            "[Virtual Desktop] No desktops found."
        )

        return

    print(
        "[Virtual Desktop] Current desktops:"
    )

    for desktop in desktops:

        number = (
            _get_desktop_number(
                desktop
            )
        )

        name = (
            _get_desktop_name(
                desktop
            )
        )

        guid = (
            _get_desktop_guid(
                desktop
            )
        )

        print(
            f"    Desktop {number + 1 if number is not None else '?'}"
            f" | Name: '{name}'"
            f" | GUID: {guid}"
        )