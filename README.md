# Void Launcher

Void Launcher turns one hotkey into a whole clean desktop for whatever you're about to do. Press a shortcut and it switches Windows to a fresh virtual desktop, opens the apps and websites you want there, mutes distractions, and sets the mood with a wallpaper. Press it again and it puts everything back exactly the way it was.

It works on Windows 10 (2004 and newer) and Windows 11, and lives quietly in your system tray so it's out of the way until you need it.

## What it does

The core idea is a **personality** (in the settings these show up as "personalities" - think of them as saved moods or workspaces, like "Gaming" or "Focus Mode"). Each personality bundles together a few things:

- A **hotkey** that turns it on and off
- A set of **apps** to launch
- A set of **websites** to open
- A **virtual desktop** of its own
- Some **system settings** (volume and Do Not Disturb)
- A **wallpaper**
- Ram Montor and Smart suggestion (comming soon)

When you press the hotkey, Void Launcher does all of this in a specific order so things land where they should:

1. It saves the state it's about to change (volume, Do Not Disturb, and the current wallpaper) so it can hand them back later.
2. If the personality uses one, it switches Windows to a fresh virtual desktop and gives that desktop the personality's real name. So "Gaming" gets an actual Windows Desktop named "Gaming".
3. It launches the configured apps onto that desktop.
4. It opens the first website in a brand-new browser window, then loads the rest of the websites as tabs in that same window, and pins the whole thing onto the personality's desktop.
5. It applies the personality's volume, Do Not Disturb, and wallpaper.

Press the hotkey again and it reverses the whole thing: it gently closes the apps and browser windows it opened, restores your volume, Do Not Disturb, and wallpaper, switches you back to the desktop you were on, and removes the personality's desktop.

## The important part: it only touches its own stuff

The one thing Void Launcher is careful never to do is interfere with things you were already using. It tracks **exactly** what it opened:

- Each app it launches is remembered as a specific process.
- Each browser window it opens is remembered as a specific window.

When you close a personality, it only closes those exact processes and that exact window. It will not touch other browser instances you already (Warning: it will close the browser it opens, including all the tabs inside it. can be changed later if people dont like this), other instances of the same app, or anything else running on your machine.

It also closes things the way you would. It asks a window to close normally (the same as pressing the X button) rather than force-killing it. So if you have an unsaved Word document open, Word gets to show its normal save prompt first. If a program refuses to close, Void Launcher leaves it alone instead of crashing it out.

## Main features

**One hotkey per workspace.** Each personality has its own shortcut, and pressing it toggles the whole environment on and off. Hotkeys reload automatically if the config changes, so you don't need to restart.

**Real named virtual desktops.** Every personality gets an actual Windows virtual desktop, named after it. Naming uses Windows 11's native API where available and a registry fallback on Windows 10, so the name shows up in Task View on both. When a personality closes, its desktop is deleted (only if Void Launcher created it) and you're put back where you were.

**Handles the browser fights back.** Browsers like Edge and Chrome love to yank the visible desktop back to Desktop One a moment after they open, which would scatter everything onto the wrong desktop. Void Launcher explicitly moves each new browser window onto the personality's desktop and keeps re-asserting that desktop for a moment after opening, so the browser stays where you wanted it.

**Volume control.** Each personality can set the system volume level, and it's restored when the personality closes.

**Do Not Disturb on both Windows 10 and 11.** It detects which Windows you're on and uses the right mechanism for each:

- On **Windows 10**, it flips the notification toast master switch in the registry.
- On **Windows 11**, it writes the correct value into the CloudStore Do Not Disturb entry.

It even restarts the per-user notification service in the background so the change actually takes effect. The previous state is remembered and put back.

**Wallpaper switching.** Each personality can set the desktop wallpaper. On close it restores your original one. Paths are handled portably so they work on any machine (more on this below) [working on getting a wallpaper per Personality desktop instead of changing all of them].

**taskbar icon.** The app hides to the system tray with a menu for opening the settings, showing or hiding the log console, and closing the app.

**A log console you can open any time.** Since the app normally runs without a window, all its activity is buffered. You can open a console from the tray menu to watch what it's doing - (IMPORTENT: If you have found the bug, send the bug in the Github Issues tab with a detailed description of the bug, if you can recreate it, and the data from the console).

**Gentle shutdown.** Exiting from the tray closes the settings window cleanly and stops the hotkey listener before the app goes away.

## How it's built

Void Launcher runs as a small background process plus a separate settings window app. The whole thing is made in Python on Windows:

- `engine.py` is the main code. It registers hotkeys, watches the config for changes, and drives the whole open/close sequence in the right order.
- `virtual_desktop.py` handles everything about virtual desktops - creating, naming, switching, deleting - using the `pyvda` library plus some registry work for names and stable GUID tracking.
- `app_handler.py` launches and closes apps and browser windows, resolving your default browser from the registry, tracking exactly what it opened, and closing things normally.
- `system_settings.py` handles volume (via pycaw), Do Not Disturb for both Windows versions, and the wallpaper.
- `json_reader.py` reads the config file, caches it, and reloads it only when it actually changes on disk. It also lets the engine notice hotkey changes live.

It runs against Python 3.14 and uses `pyvda` for desktops and window moves, `pycaw` for volume, `pystray` for the tray icon, and `keyboard` for the global hotkeys.

## Getting started

### Running it

The finished app is a folder containing `VoidLauncher.exe` (plus its `_internal`, `scripts`, and `UI` folders). Just run `VoidLauncher.exe` - nothing to install. It starts hidden in the system tray.

The `UI` folder also contains `VoidLauncherUI.exe`, which is the settings window. You can open it from the tray menu by right-clicking it and tapping on settings, and Void Launcher closes it automatically when the app exits.

### Setting up your first personality

1. Run `VoidLauncher.exe`.
2. Open Settings from the tray icon.
3. Create a personality, give it a name and a hotkey, and turn on whichever sections you want.
4. Make sure to Save - the hotkey registers immediately without restarting.

You can have as many personalities as you like, each with its own hotkey.

A quick example: a "Focus Mode" personality might use `Ctrl+Alt+F`, launch word, open your project's site and a chat app, drop the volume, turn on Do Not Disturb, and switch to its own desktop. When you're done, press the same hotkey and everything goes back to normal.

## How the config works (mostly optional)

You will almost never need to touch the config file by hand - it lives at `scripts\config.json` inside the app folder and is written through the settings window. The one thing the settings window doesn't cover (yet) is auto-start, which is only controllable by editing the file. We'll walk you through that below.

The config is one JSON document with a few top-level sections:

```json
{
  "global-settings": { ... },
  "personalities": [ { ... }, ... ],
  "feature-ram-monitor": { ... },
  "feature-smart-suggestions": { ... }
}
```

### `global-settings`

At the moment, this only holds `run-at-startup`. When enabled, Void Launcher registers itself in the Windows Startup registry (`HKCU\...\CurrentVersion\Run`) so it launches when you sign in. When disabled, it removes that entry.

**Editing this one requires touching the file** because there's no toggle for it in the settings window yet:

```json
"global-settings": {
  "run-at-startup": {
    "enabled": true
  }
}
```

Set `enabled` to `true` to auto-start, or `false` to turn it off. Save the file and restart Void Launcher - the startup registry entry is updated when the app starts.

### `personalities`

This is a list. Each entry describes one personality:

```json
{
  "name": "Focus Mode",
  "enabled": true,
  "trigger-shortcut": "ctrl+alt+f",
  "apps-to-launch": {
    "enabled": true,
    "paths": "C:\\Program Files\\...\\WINWORD.EXE"
  },
  "tabs-to-open": {
    "enabled": true,
    "urls": "https://github.com, https://chatgpt.com"
  },
  "virtual-desktop-switch": {
    "enabled": true,
    "target-desktop-name": "Focus"
  },
  "system-settings-automation": {
    "enabled": true,
    "volume-level": 40,
    "do-not-disturb": true
  },
  "wallpaper-switch": {
    "enabled": true,
    "wallpaper-path": "scripts\\wallpaper_example.png"
  }
}
```

- `name` - the personality's name, and what its virtual desktop will be called if you don't set a different `target-desktop-name`.
- `enabled` - whether this personality registers its hotkey (set to `false` to temporarily disable one without deleting it).
- `trigger-shortcut` - the global hotkey string (see below for the format). Disabled if left empty.
- `apps-to-launch.paths` - a comma-separated list of application paths. Each app is launched in its own process and closed gently when the personality closes, so your own instances of the same app are left alone.
- `tabs-to-open.urls` - a comma-separated list of website URLs. The first becomes its own browser window; the rest open as tabs in that window. It uses your default browser, falling back through a list of common ones.
- `virtual-desktop-switch` - turn this off if you don't want the personality to manage its own desktop.
- `system-settings-automation` - `volume-level` from `0` to `100`, and `do-not-disturb` as `true`/`false`. These are restored when the personality closes.
- `wallpaper-switch` - see the note on wallpaper paths below.

**Hotkey format.** Shortcut strings use the `keyboard` library format. Modifiers are written out and separated by `+`, e.g. `ctrl+alt+f`, `ctrl+win+z`, `ctrl+shift+alt+f`. Common aliases include `ctrl`, `alt`, `shift`, `win` (Windows key), `space`, and function keys like `f1`.

### `feature-ram-monitor` and `feature-smart-suggestions`

These two sections exist for upcoming features. `feature-ram-monitor` has an `enabled` flag and a `max-allowed-percentage` threshold; `feature-smart-suggestions` has an `enabled` flag and a scan interval. They're currently off by default in the shipped config and don't do anything yet - they're placeholder plumbing for what's coming.

### Wallpaper paths that work anywhere

`wallpaper-path` is written **soft-coded** on purpose, so it resolves on any machine without any hard-coded `C:\Users\<name>\...` values. Several forms are accepted:

- `scripts\wallpaper_example.png` - a path relative to the app folder. A copy of `wallpaper_example.png` is bundled inside the app when it's built, so this works on every machine.
- `~\\Pictures\\example.png` - relative to the user's home folder.
- `%USERPROFILE%\\Pictures\\example.png` - classic environment-variable form.
- `C:\\path\\to\\image.png` - a normal absolute path, if you really want one.

The resolver tries the relative path against the app's own folder, then the copy bundled inside the app, then the source folder, and always hands Windows an absolute path - so a relative value never ends up pointing at nothing (which is what caused black wallpapers in earlier builds). On Windows you may need to double the backslashes in the JSON.

You can swap in your own image by keeping it named `wallpaper_example.png` in the `scripts` folder, or point `wallpaper-path` at any image file with one of the portably-resolvable forms above.

### When to edit the file

- To enable or disable **auto-start**, which has no settings-window toggle yet.
- To make advanced changes outside what the settings window exposes.

After editing, either restart Void Launcher or just save - hotkeys pick up config changes automatically (the engine watches the file and re-registers shortcuts when it changes).

## What's on the roadmap

- **RAM monitor** - watch memory usage against a threshold and if its to high warn you that it might be slow and other things.
- **Smart suggestions** - suggest personalities based on your pc usage.

These are wired into the config as placeholders already (`feature-ram-monitor` and `feature-smart-suggestions`), so they'll slot in without breaking the file.

## Troubleshooting

**Nothing happens when I press a hotkey.** Open the log console from the tray menu and look for a line about registering the hotkey. The most common cause is a shortcut already being used by another program or another personality (duplicate shortcuts are skipped). Make sure the personality is `enabled` and has a `trigger-shortcut`.

**My app didn't launch.** Check the log. App entries that point at paths that don't exist on this machine are skipped (and logged), rather than crashed on.

**Websites opened on the wrong desktop.** This used to be a problem with Edge/Chrome flipping the visible desktop right after opening. The launcher re-asserts the personality's desktop after opening and moves the window explicitly, so it should stay put.

**The wallpaper is black.** Make sure `wallpaper-path` uses one of the resolvable forms above (e.g. `scripts\wallpaper_example.png`). A bare relative path with no matching file on the launch folder reverts to the bundled example. Check the console - if it says "Wallpaper not found", the path didn't resolve to an existing file.

**The personality won't disappear.** If closing a personality finds an app that refused to close (for example, because it's waiting on a save prompt), Void Launcher deliberately leaves it running rather than killing it. That app stays open on the personality's desktop by design, and the desktop isn't deleted while it's in use.

## Notes

- Void Launcher manages real Windows virtual desktops, which can take a moment to settle on slower machines, and relies on Windows itself for the desktop-creation and naming operations.
- This is a personal tool built to solve the "everything in one place gets messy" problem. It's designed to get out of your way and put things back the way it found them.
- If you have any bugs or recommendations, pop them into the GitHub issues form with proper instructions. I'll be happy to help.
